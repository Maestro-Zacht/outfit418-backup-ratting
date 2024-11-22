from collections import defaultdict

from celery import shared_task, group
from celery_once import QueueOnce

from django.db import transaction
from django.utils import timezone

from allianceauth.services.hooks import get_extension_logger
from allianceauth.authentication.models import CharacterOwnership

from allianceauth_pve.models import Rotation, Entry, EntryCharacter

from corptools.models import CharacterAudit, CharacterAsset
from corptools.task_helpers.char_tasks import get_token

from .utils import get_or_create_char, get_user_or_fake, get_default_user, get_ship_names
from .models import EntryCreator, ShareUser, CharacterAuditLoginData
from .provider import esi


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
            name=rotation_data['name'],
            actual_total=int(rotation_data['actual_total']),
            tax_rate=rotation_data['tax_rate'],
            is_closed=rotation_data['is_closed'],
            is_paid_out=rotation_data['is_paid_out'],
            priority=rotation_data['priority'],
        )

        if rotation_data['name'] == '':
            rotation.name = f"Rotation {rotation.pk}"
            rotation.save()

        Rotation.objects.filter(pk=rotation.pk).update(
            created_at=rotation_data['created_at'],
            closed_at=rotation_data['closed_at'],
        )

        for entry_data in rotation_data['entries']:

            if len(entry_data['shares']) > 0:
                creator = get_user_or_fake(entry_data['created_by'])
                char = get_or_create_char(entry_data['created_by'])

                entry = rotation.entries.create(
                    estimated_total=entry_data['estimated_total'],
                    created_by=creator,
                )

                if creator == fake_user:
                    EntryCreator.objects.create(
                        entry=entry,
                        creator_character=char
                    )

                Entry.objects.filter(pk=entry.pk).update(
                    created_at=entry_data['created_at'],
                    updated_at=entry_data['updated_at'],
                )

                role = entry.roles.create(
                    name='Krab',
                    value=1,
                )

                for share_data in entry_data['shares']:
                    user = get_user_or_fake(share_data['character'])
                    character = get_or_create_char(share_data['character'])

                    share = entry.ratting_shares.create(
                        user=user,
                        user_character=character,
                        role=role,
                        site_count=share_data['share_count'],
                        helped_setup=share_data['helped_setup'],
                    )

                    if user == fake_user:
                        ShareUser.objects.create(
                            share=share,
                            character=character
                        )
        if rotation.entries.count() == 0:
            rotation.delete()


@shared_task
def update_fake_users():
    characters = ShareUser.objects.all().values('character')

    for ownership in CharacterOwnership.objects.filter(character__in=characters):
        with transaction.atomic():
            shares_qs = ShareUser.objects.filter(character=ownership.character)
            EntryCharacter.objects.filter(pk__in=shares_qs.values('share_id')).update(user=ownership.user)
            shares_qs.delete()

    characters = EntryCreator.objects.all().values('creator_character')

    for ownership in CharacterOwnership.objects.filter(character__in=characters):
        with transaction.atomic():
            entry_qs = EntryCreator.objects.filter(creator_character=ownership.character)
            Entry.objects.filter(pk__in=entry_qs.values('entry_id')).update(created_by=ownership.user)
            entry_qs.delete()


@shared_task(base=QueueOnce, once={'keys': ['pk'], 'graceful': True})
def update_character_login(pk, force_refresh=False):
    char = CharacterAudit.objects.get(pk=pk)
    login_data = CharacterAuditLoginData.objects.get_or_create(characteraudit=char)[0]

    if force_refresh or login_data.last_update is None or login_data.last_update < timezone.now() - timezone.timedelta(hours=1):
        token = get_token(char.character.character_id, ['esi-location.read_online.v1'])
        if token:
            result = (
                esi.client
                .Location
                .get_characters_character_id_online(
                    character_id=char.character.character_id,
                    token=token.valid_access_token()
                )
                .results()
            )
            if result['online']:
                login_data.last_login = timezone.now()
                login_data.last_update = timezone.now()
            elif 'last_login' in result:
                login_data.last_login = result['last_login']
                login_data.last_update = timezone.now()
            login_data.save()


@shared_task
def update_all_characters_logins(force_refresh=False):
    pks = CharacterAudit.objects.values_list('pk', flat=True)
    group(update_character_login.s(pk=pk) for pk in pks).delay(force_refresh=force_refresh)


@shared_task
def update_character_ship_names(character_id: int, item_ids: list[int]):
    token = get_token(character_id, ['esi-assets.read_assets.v1'])
    if token:
        get_ship_names(token, item_ids)


@shared_task
def update_ship_names():
    thannys = CharacterAsset.objects.filter(type_name_id=23911).select_related('character__character')
    thanny_dict = defaultdict(list)

    for thanny in thannys:
        thanny_dict[thanny.character.character.character_id].append(thanny.item_id)

    group(
        update_character_ship_names.si(character_id=char_id, item_ids=item_ids)
        for char_id, item_ids in thanny_dict.items()
    ).delay()
