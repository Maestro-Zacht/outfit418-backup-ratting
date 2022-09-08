from django.db import models

from allianceauth_pve.models import Entry


class EntryCreator(models.Model):
    entry = models.OneToOneField(Entry, on_delete=models.CASCADE, related_name='+')
    creator_characterid = models.PositiveIntegerField()
