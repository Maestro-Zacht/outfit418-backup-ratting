from django import template

from allianceauth.eveonline.models import EveCharacter

register = template.Library()


@register.filter
def ct_is_active(char: EveCharacter) -> bool:
    return char.characteraudit.is_active() if hasattr(char, 'characteraudit') else False
