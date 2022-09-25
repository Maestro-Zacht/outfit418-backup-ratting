from django.contrib.auth.models import User

from allianceauth.eveonline.models import EveCharacter
from allianceauth.authentication.models import CharacterOwnership


def get_or_create_char(character_id: int) -> EveCharacter:
    if character_id == 1:
        character_id = 2120413474

    char = EveCharacter.objects.get_character_by_id(character_id)

    if char is None:
        char = EveCharacter.objects.create_character(character_id)

    return char


def get_default_user() -> User:
    char = get_or_create_char(2120413474)
    return char.character_ownership.user


def get_user_or_fake(character_id) -> User:
    char = get_or_create_char(character_id)
    try:
        ownership = CharacterOwnership.objects.get(character=char)
        return ownership.user
    except CharacterOwnership.DoesNotExist:
        return get_default_user()
