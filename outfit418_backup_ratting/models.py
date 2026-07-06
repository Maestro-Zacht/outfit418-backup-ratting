from datetime import datetime
from datetime import timezone as dt_timezone
from typing import TYPE_CHECKING

from allianceauth.eveonline.models import EveCharacter
from allianceauth_pve.models import Entry, EntryCharacter
from corptools.models import CharacterAudit
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from eve_sde.models import SolarSystem
from opcalendar.models import (
    Event,
    EventCategory,
    EventHost,
    EventMember,
    EventVisibility,
)


class General(models.Model):
    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("audit_corp", "Can audit corp members' alts"),
            ("find_jeremy", "Can find Jeremy"),
            ("view_member_activity", "Can view member activity"),
        )


class EntryCreator(models.Model):
    entry = models.OneToOneField(Entry, on_delete=models.CASCADE, related_name="+")
    creator_character = models.ForeignKey(
        EveCharacter, on_delete=models.RESTRICT, related_name="+"
    )


class ShareUser(models.Model):
    share = models.OneToOneField(
        EntryCharacter, on_delete=models.CASCADE, related_name="+"
    )
    character = models.ForeignKey(
        EveCharacter, on_delete=models.RESTRICT, related_name="+"
    )


class CharacterAuditLoginData(models.Model):
    characteraudit = models.OneToOneField(
        CharacterAudit, on_delete=models.CASCADE, related_name="+"
    )

    last_login = models.DateTimeField(null=True, blank=True)
    last_logout = models.DateTimeField(null=True, blank=True)
    is_online = models.BooleanField(default=False)

    last_update = models.DateTimeField(null=True, blank=True)
    last_modified = models.DateTimeField(null=True, blank=True)

    if TYPE_CHECKING:
        member_activity: "MemberActivity"

    def set_last_modified_from_header(self, last_modified_header: str):
        self.last_modified = datetime.strptime(
            last_modified_header,
            "%a, %d %b %Y %H:%M:%S GMT",
        ).replace(tzinfo=dt_timezone.utc)


class MemberActivity(models.Model):
    login_data = models.OneToOneField(
        CharacterAuditLoginData,
        on_delete=models.CASCADE,
        related_name="member_activity",
    )

    last_modified = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(null=True, blank=True)

    def set_last_modified_from_header(self, last_modified_header: str):
        self.last_modified = datetime.strptime(
            last_modified_header,
            "%a, %d %b %Y %H:%M:%S GMT",
        ).replace(tzinfo=dt_timezone.utc)


class MemberActivityLocation(models.Model):
    member_activity = models.ForeignKey(
        MemberActivity,
        on_delete=models.CASCADE,
        related_name="locations",
    )
    system = models.ForeignKey(
        SolarSystem,
        on_delete=models.RESTRICT,
        related_name="+",
    )

    is_online = models.BooleanField()
    is_docked = models.BooleanField()

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)


class EventBackup(models.Model):
    DAILY = "DD"
    WEEKLY = "WE"
    MONTHLY = "MM"
    YEARLY = "YY"

    REPEAT_INTERVAL = [
        (DAILY, "Daily"),
        (WEEKLY, "Weekly"),
        (MONTHLY, "Monthly"),
        (YEARLY, "Yearly"),
    ]

    operation_type = models.ForeignKey(
        EventCategory,
        null=True,
        on_delete=models.CASCADE,
    )
    title = models.CharField(
        max_length=200,
    )
    host = models.ForeignKey(
        EventHost,
        on_delete=models.CASCADE,
    )
    doctrine = models.CharField(
        max_length=254,
    )
    formup_system = models.CharField(
        max_length=254,
    )
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    repeat_event = models.CharField(
        max_length=32,
        default=False,
        null=True,
        blank=True,
        choices=REPEAT_INTERVAL,
    )
    repeat_times = models.IntegerField(
        default=False,
        null=True,
        blank=True,
    )
    fc = models.CharField(
        max_length=254,
    )
    event_visibility = models.ForeignKey(
        EventVisibility,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    external = models.BooleanField(
        default=False,
        null=True,
    )
    created_date = models.DateTimeField(
        default=timezone.now,
    )
    eve_character = models.ForeignKey(
        EveCharacter,
        null=True,
        on_delete=models.SET_NULL,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )

    deleted_on = models.DateTimeField(auto_now_add=True)

    @classmethod
    def create_from_event(cls, event: Event):
        res = cls.objects.create(
            operation_type=event.operation_type,
            title=event.title,
            host=event.host,
            doctrine=event.doctrine,
            formup_system=event.formup_system,
            description=event.description,
            start_time=event.start_time,
            end_time=event.end_time,
            repeat_event=event.repeat_event,
            repeat_times=event.repeat_times,
            fc=event.fc,
            event_visibility=event.event_visibility,
            external=event.external,
            eve_character=event.eve_character,
            user=event.user,
        )

        for member in EventMember.objects.filter(event=event):
            EventMemberBackup.objects.create(
                event=res,
                character=member.character,
                status=member.status,
                comment=member.comment,
            )

        return res

    def restore_event(self) -> Event:
        res = Event.objects.create(
            operation_type=self.operation_type,
            title=self.title,
            host=self.host,
            doctrine=self.doctrine,
            formup_system=self.formup_system,
            description=self.description,
            start_time=self.start_time,
            end_time=self.end_time,
            repeat_event=self.repeat_event,
            repeat_times=self.repeat_times,
            fc=self.fc,
            event_visibility=self.event_visibility,
            external=self.external,
            eve_character=self.eve_character,
            user=self.user,
        )

        for member in EventMemberBackup.objects.filter(event=self):
            EventMember.objects.create(
                event=res,
                character=member.character,
                status=member.status,
                comment=member.comment,
            )

        self.delete()

        return res


class EventMemberBackup(models.Model):
    class Status(models.TextChoices):
        ATTENDING = "A", "Attending"
        MAYBE = "M", "Maybe"
        DECLINED = "D", "Declined"

    event = models.ForeignKey(EventBackup, on_delete=models.CASCADE)
    character = models.ForeignKey(
        EveCharacter,
        null=True,
        on_delete=models.SET_NULL,
        help_text="Event creator main character",
    )
    status = models.CharField(
        max_length=1,
        choices=Status.choices,
        default=Status.ATTENDING,
    )
    comment = models.CharField(
        max_length=100, blank=True, help_text="Optional comment about the event"
    )

    class Meta:
        unique_together = ["event", "character"]
