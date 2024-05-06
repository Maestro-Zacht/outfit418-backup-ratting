from django.db import models

from allianceauth_pve.models import Entry, EntryCharacter

from allianceauth.eveonline.models import EveCharacter

from corptools.models import CharacterAudit


class General(models.Model):
    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ('audit_corp', "Can audit corp members' alts"),
        )


class EntryCreator(models.Model):
    entry = models.OneToOneField(Entry, on_delete=models.CASCADE, related_name='+')
    creator_character = models.ForeignKey(EveCharacter, on_delete=models.RESTRICT, related_name='+')


class ShareUser(models.Model):
    share = models.OneToOneField(EntryCharacter, on_delete=models.CASCADE, related_name='+')
    character = models.ForeignKey(EveCharacter, on_delete=models.RESTRICT, related_name='+')


class CharacterAuditLoginData(models.Model):
    characteraudit = models.OneToOneField(CharacterAudit, on_delete=models.CASCADE, related_name='+')
    last_login = models.DateTimeField(null=True, blank=True)
    last_update = models.DateTimeField(null=True, blank=True)
