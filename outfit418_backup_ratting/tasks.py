from celery import shared_task

from django.db import transaction

from allianceauth.services.hooks import get_extension_logger
from allianceauth.authentication.models import CharacterOwnership

from allianceauth_pve.models import Rotation, Entry, EntryCharacter

from .utils import get_or_create_char, get_user_or_fake, get_fake_user
from .models import EntryCreator, ShareUser


logger = get_extension_logger(__name__)


@shared_task
def fetch_char(char_id):
    if char_id != 1:
        get_or_create_char(char_id)


@shared_task
@transaction.atomic
def save_import(data):
    fake_user = get_fake_user()

    for rotation_data in data:
        rotation = Rotation.objects.create(
            name=rotation_data['name'],
            actual_total=rotation_data['actual_total'],
            tax_rate=rotation_data['tax_rate'],
            is_closed=rotation_data['is_closed'],
            is_paid_out=rotation_data['is_paid_out'],
            priority=rotation_data['priority'],
        )

        Rotation.objects.filter(pk=rotation.pk).update(
            created_at=rotation_data['created_at'],
            closed_at=rotation_data['closed_at'],
        )

        for entry_data in rotation_data['entries']:
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
                    estimated_share_total=share_data['estimated_share_total'],
                    actual_share_total=share_data['actual_share_total']
                )

                if user == fake_user:
                    ShareUser.objects.create(
                        share=share,
                        character=character
                    )


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
