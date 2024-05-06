from django.db.models.signals import post_save
from django.dispatch import receiver

from corptools.models import CharacterAudit

from .tasks import update_character_login


@receiver(post_save, sender=CharacterAudit)
def update_login_data(sender, instance, **kwargs):
    update_character_login.apply_async(kwargs={'pk': instance.pk, 'force_refresh': False}, countdown=10)
