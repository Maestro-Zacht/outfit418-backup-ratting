from allianceauth import hooks
from allianceauth.services.hooks import UrlHook, MenuItemHook
from allianceauth.services.hooks import get_extension_logger

from . import urls

logger = get_extension_logger(__name__)


class Outfit418BackupRattingItemHook(MenuItemHook):
    def __init__(self):
        super().__init__("Outfit418 Backup Ratting", "fas fa-wallet", "outfit418backup:index", navactive=['outfit418backup:index', 'outfit418backup:dashboard'])

    def render(self, request):
        if request.user.is_superuser:
            return super().render(request)
        return ''


class Outfit418AuditHook(MenuItemHook):
    def __init__(self):
        super().__init__("418 Audit", "fas fa-search", "outfit418backup:audit", navactive=['outfit418backup:audit'])

    def render(self, request):
        if request.user.has_perm('outfit418_backup_ratting.audit_corp'):
            return super().render(request)
        return ''


class Outfit418FindJeremyHook(MenuItemHook):
    def __init__(self):
        super().__init__("Find Jeremy", "fas fa-search", "outfit418backup:find_jeremy", navactive=['outfit418backup:find_jeremy'])

    def render(self, request):
        if request.user.has_perm('outfit418_backup_ratting.find_jeremy'):
            return super().render(request)
        return ''


@hooks.register('menu_item_hook')
def register_menu():
    return Outfit418BackupRattingItemHook()


@hooks.register('menu_item_hook')
def register_audit_menu():
    return Outfit418AuditHook()


@hooks.register('menu_item_hook')
def register_find_jeremy_menu():
    return Outfit418FindJeremyHook()


@hooks.register('url_hook')
def register_urls():
    return UrlHook(urls, 'outfit418backup', 'outfit418backup/')
