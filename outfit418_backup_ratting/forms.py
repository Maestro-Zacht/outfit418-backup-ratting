from django import forms


class BackupForm(forms.Form):
    file = forms.FileField(allow_empty_file=False)
