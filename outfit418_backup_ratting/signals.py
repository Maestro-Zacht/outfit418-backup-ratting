from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from corptools.models import CharacterAudit

from opcalendar.models import Event

from .tasks import update_character_login
from .models import EventBackup


@receiver(post_save, sender=CharacterAudit)
def update_login_data(sender, instance, **kwargs):
    update_character_login.apply_async(kwargs={'pk': instance.pk, 'force_refresh': False}, countdown=10)


@receiver(pre_delete, sender=Event)
def backup_event(sender, instance, **kwargs):
    EventBackup.create_from_event(instance)
