from django.db.models.signals import pre_delete
from django.dispatch import receiver
from opcalendar.models import Event

from .models import EventBackup


@receiver(pre_delete, sender=Event)
def backup_event(sender, instance, **kwargs):
    EventBackup.create_from_event(instance)
