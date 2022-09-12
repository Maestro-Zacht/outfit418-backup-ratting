from django.db import models

from allianceauth_pve.models import Entry, EntryCharacter

from allianceauth.eveonline.models import EveCharacter


class EntryCreator(models.Model):
    entry = models.OneToOneField(Entry, on_delete=models.CASCADE, related_name='+')
    creator_character = models.ForeignKey(EveCharacter, on_delete=models.RESTRICT, related_name='+')


class ShareUser(models.Model):
    share = models.OneToOneField(EntryCharacter, on_delete=models.CASCADE, related_name='+')
    character = models.ForeignKey(EveCharacter, on_delete=models.RESTRICT, related_name='+')
