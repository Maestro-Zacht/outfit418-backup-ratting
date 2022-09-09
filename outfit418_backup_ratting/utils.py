from django.contrib.auth.models import User

from allianceauth.eveonline.models import EveCharacter
from allianceauth.authentication.models import CharacterOwnership


def get_or_create_char(character_id: int) -> EveCharacter:
    char = EveCharacter.objects.get_character_by_id(character_id)

    if char is None:
        char = EveCharacter.objects.create_character(character_id)

    return char


def get_fake_user() -> User:
    try:
        user: User = User.objects.get(username='Outfit418')
    except User.DoesNotExist:
        user: User = User.objects.create_user('Backup User', is_active=False)
        user.set_unusable_password()  # prevent login via password
        user.save()

    return user


def get_user_or_fake(character_id) -> User:
    char = get_or_create_char(character_id)
    try:
        ownership = CharacterOwnership.objects.get(character=char)
        return ownership.user
    except CharacterOwnership.DoesNotExist:
        return get_fake_user()
