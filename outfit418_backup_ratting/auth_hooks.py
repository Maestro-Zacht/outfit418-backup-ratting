from allianceauth import hooks
from allianceauth.services.hooks import UrlHook, MenuItemHook
from allianceauth.services.hooks import get_extension_logger

from . import urls

logger = get_extension_logger(__name__)


class Outfit418BackupRattingItemHook(MenuItemHook):
    def __init__(self):
        super().__init__("Outfit418 Backup Ratting", "fas fa-wallet", "outfit418backup:index", navactive=['outfit418backup:'])

    def render(self, request):
        if request.user.is_superuser:
            return super().render(request)
        return ''


@hooks.register('menu_item_hook')
def register_menu():
    return Outfit418BackupRattingItemHook()


@hooks.register('url_hook')
def register_urls():
    return UrlHook(urls, 'outfit418backup', 'outfit418backup/')
