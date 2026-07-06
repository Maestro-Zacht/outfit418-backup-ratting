from collections import defaultdict

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.services.hooks import get_extension_logger
from allianceauth_pve.models import Entry, EntryCharacter, Rotation
from celery import group, shared_task
from celery_once import QueueOnce
from corptools.models import CharacterAsset, CharacterAudit
from django.db import transaction
from django.utils import timezone
from esi.exceptions import HTTPNotModified

from .models import (
    CharacterAuditLoginData,
    EntryCreator,
    MemberActivity,
    MemberActivityLocation,
    ShareUser,
)
from .provider import esi
from .utils import (
    get_default_user,
    get_or_create_char,
    get_ship_names,
    get_token,
    get_user_or_fake,
)

logger = get_extension_logger(__name__)


@shared_task
def fetch_char(char_id):
    if char_id != 1:
        get_or_create_char(char_id)


@shared_task
@transaction.atomic
def save_import(data):
    fake_user = get_default_user()

    for rotation_data in data:
        rotation = Rotation.objects.create(
            name=rotation_data["name"],
            actual_total=int(rotation_data["actual_total"]),
            tax_rate=rotation_data["tax_rate"],
            is_closed=rotation_data["is_closed"],
            is_paid_out=rotation_data["is_paid_out"],
            priority=rotation_data["priority"],
        )

        if rotation_data["name"] == "":
            rotation.name = f"Rotation {rotation.pk}"
            rotation.save()

        Rotation.objects.filter(pk=rotation.pk).update(
            created_at=rotation_data["created_at"],
            closed_at=rotation_data["closed_at"],
        )

        for entry_data in rotation_data["entries"]:
            if len(entry_data["shares"]) > 0:
                creator = get_user_or_fake(entry_data["created_by"])
                char = get_or_create_char(entry_data["created_by"])

                entry = rotation.entries.create(
                    estimated_total=entry_data["estimated_total"],
                    created_by=creator,
                )

                if creator == fake_user:
                    EntryCreator.objects.create(entry=entry, creator_character=char)

                Entry.objects.filter(pk=entry.pk).update(
                    created_at=entry_data["created_at"],
                    updated_at=entry_data["updated_at"],
                )

                role = entry.roles.create(
                    name="Krab",
                    value=1,
                )

                for share_data in entry_data["shares"]:
                    user = get_user_or_fake(share_data["character"])
                    character = get_or_create_char(share_data["character"])

                    share = entry.ratting_shares.create(
                        user=user,
                        user_character=character,
                        role=role,
                        site_count=share_data["share_count"],
                        helped_setup=share_data["helped_setup"],
                    )

                    if user == fake_user:
                        ShareUser.objects.create(share=share, character=character)
        if rotation.entries.count() == 0:
            rotation.delete()


@shared_task
def update_fake_users():
    characters = ShareUser.objects.all().values("character")

    for ownership in CharacterOwnership.objects.filter(character__in=characters):
        with transaction.atomic():
            shares_qs = ShareUser.objects.filter(character=ownership.character)
            EntryCharacter.objects.filter(pk__in=shares_qs.values("share_id")).update(
                user=ownership.user
            )
            shares_qs.delete()

    characters = EntryCreator.objects.all().values("creator_character")

    for ownership in CharacterOwnership.objects.filter(character__in=characters):
        with transaction.atomic():
            entry_qs = EntryCreator.objects.filter(
                creator_character=ownership.character
            )
            Entry.objects.filter(pk__in=entry_qs.values("entry_id")).update(
                created_by=ownership.user
            )
            entry_qs.delete()


@shared_task(base=QueueOnce, once={"keys": ["pk"], "graceful": True})
def update_character_login(pk, force_refresh=False):
    char: CharacterAudit = CharacterAudit.objects.select_related("character").get(pk=pk)
    login_data = CharacterAuditLoginData.objects.get_or_create(characteraudit=char)[0]

    token = get_token(char.character.character_id, ["esi-location.read_online.v1"])
    if token:
        try:
            result, response = esi.client.Location.GetCharactersCharacterIdOnline(
                character_id=char.character.character_id, token=token
            ).result(
                last_modified=login_data.last_modified,
                force_refresh=force_refresh,
                return_response=True,
            )
        except HTTPNotModified as e:
            login_data.set_last_modified_from_header(e.headers.get("Last-Modified"))
            login_data.last_update = timezone.now()
            login_data.save()
        else:
            login_data.is_online = result.online
            login_data.last_logout = result.last_logout

            if result.last_login is not None:
                login_data.last_login = result.last_login
            elif result.online:
                login_data.last_login = timezone.now()

            login_data.set_last_modified_from_header(
                response.headers.get("Last-Modified")
            )
            login_data.last_update = timezone.now()
            login_data.save()

        update_character_location.delay(pk=pk, force_refresh=force_refresh)


@shared_task
def update_all_characters_logins(force_refresh=False):
    pks = CharacterAudit.objects.values_list("pk", flat=True)
    group(update_character_login.s(pk=pk) for pk in pks).delay(
        force_refresh=force_refresh
    )


@shared_task(base=QueueOnce, once={"keys": ["pk"], "graceful": True})
def update_character_location(pk, force_refresh=False):
    char: CharacterAudit = CharacterAudit.objects.select_related("character").get(pk=pk)
    login_data = CharacterAuditLoginData.objects.get(characteraudit=char)
    member_activity = MemberActivity.objects.get_or_create(login_data=login_data)[0]

    token = get_token(char.character.character_id, ["esi-location.read_location.v1"])
    if token:
        try:
            result, response = esi.client.Location.GetCharactersCharacterIdLocation(
                character_id=char.character.character_id, token=token
            ).result(
                last_modified=member_activity.last_modified,
                force_refresh=force_refresh,
                return_response=True,
            )
        except HTTPNotModified as e:
            member_activity.set_last_modified_from_header(
                e.headers.get("Last-Modified")
            )
            member_activity.last_updated = timezone.now()
            member_activity.save()
        else:
            current_activity_location = MemberActivityLocation.objects.get_or_create(
                member_activity=member_activity,
                end_time=None,
                defaults={
                    "system_id": result.solar_system_id,
                    "is_online": login_data.is_online,
                    "start_time": timezone.now(),
                },
            )[0]
            if (
                result.solar_system_id != current_activity_location.system_id
                or login_data.is_online != current_activity_location.is_online
            ):
                current_activity_location.end_time = timezone.now()
                current_activity_location.save()

                MemberActivityLocation.objects.create(
                    member_activity=member_activity,
                    system_id=result.solar_system_id,
                    is_online=login_data.is_online,
                    start_time=timezone.now(),
                )

            member_activity.set_last_modified_from_header(
                response.headers.get("Last-Modified")
            )
            member_activity.last_updated = timezone.now()
            member_activity.save()


@shared_task
def update_character_ship_names(character_id: int, item_ids: list[int]):
    token = get_token(character_id, ["esi-assets.read_assets.v1"])
    if token:
        get_ship_names(token, item_ids)


@shared_task
def update_ship_names():
    thannys = CharacterAsset.objects.filter(type_name_id=23911).select_related(
        "character__character"
    )
    thanny_dict = defaultdict(list)

    for thanny in thannys:
        thanny_dict[thanny.character.character.character_id].append(thanny.item_id)

    group(
        update_character_ship_names.si(character_id=char_id, item_ids=item_ids)
        for char_id, item_ids in thanny_dict.items()
    ).delay()
