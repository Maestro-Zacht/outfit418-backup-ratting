from typing import TYPE_CHECKING

from allianceauth.eveonline.models import EveCharacter
from django import forms

if TYPE_CHECKING:
    from django.contrib.auth.models import User

# Matches the jquery-datetimepicker format 'Y-m-d H:i'
DATETIME_FORMAT = "%Y-%m-%d %H:%M"


class BackupForm(forms.Form):
    file = forms.FileField(allow_empty_file=False)


def visible_mains(user: "User"):
    qs = EveCharacter.objects.filter(userprofile__isnull=False)
    if not user.is_superuser:
        try:
            main = user.profile.main_character
        except AttributeError:
            return EveCharacter.objects.none()
        qs = qs.filter(corporation_id=main.corporation_id)
    return qs.order_by("character_name")


class MemberActivityFilterForm(forms.Form):
    main_character = forms.ModelChoiceField(
        queryset=EveCharacter.objects.none(),
        label="Main character",
    )
    # Naive inputs are interpreted in the server TIME_ZONE (UTC = EVE time)
    start = forms.DateTimeField(
        input_formats=[DATETIME_FORMAT],
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    end = forms.DateTimeField(
        input_formats=[DATETIME_FORMAT],
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["main_character"].queryset = visible_mains(user)

    def clean(self):
        cleaned = super().clean()
        if (
            cleaned.get("start")
            and cleaned.get("end")
            and cleaned["start"] >= cleaned["end"]
        ):
            msg = "Start must be before end."
            raise forms.ValidationError(msg)
        return cleaned
