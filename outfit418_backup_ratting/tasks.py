from celery import shared_task

from django.db import transaction

from allianceauth.services.hooks import get_extension_logger

from allianceauth_pve.models import Rotation, Entry, EntryCharacter

from .utils import get_or_create_char, get_user_or_fake, get_fake_user
from .models import EntryCreator, ShareUser


logger = get_extension_logger(__name__)


@shared_task
@transaction.atomic
def save_rotation(rotation_data):
    fake_user = get_fake_user()

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
def save_import(data):
    for rotation in data['rotations']:
        save_rotation.delay(rotation)


@shared_task
def update_shares_users():
    fake_user = get_fake_user()

    for character_id in EntryCharacter.objects.filter(user=fake_user).values_list('user_character_id', flat=True).distinct():
        user = get_user_or_fake(character_id)
        if user != fake_user:
            EntryCharacter.objects.filter(user_character_id=character_id).update(user=user)


@shared_task
def update_entries_users():
    fake_user = get_fake_user()

    for entry_creator in EntryCreator.objects.all().values_list('creator_characterid', flat=True).distinct():
        user = get_user_or_fake(entry_creator)
        if user != fake_user:
            entries_query = EntryCreator.objects.filter(creator_characterid=entry_creator).values('entry_id')
            Entry.objects.filter(pk__in=entries_query).update(created_by=user)


@shared_task
def update_fake_users():
    update_entries_users.delay()
    update_shares_users.delay()
