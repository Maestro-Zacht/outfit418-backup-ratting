from esi.clients import EsiClientProvider

from . import __version__

esi = EsiClientProvider(app_info_text=f"outfit418_backup_ratting v{__version__}")
