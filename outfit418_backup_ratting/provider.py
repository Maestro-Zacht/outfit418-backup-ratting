from esi.openapi_clients import ESIClientProvider

from . import __version__

esi_compatibility_date = "2026-06-09"
github_url = "https://github.com/Maestro-Zacht/outfit418-backup-ratting"
app_name = "outfit418-backup-ratting"

esi = ESIClientProvider(
    compatibility_date=esi_compatibility_date,
    ua_appname=app_name,
    ua_version=__version__,
    ua_url=github_url,
    operations=[
        "GetCharactersCharacterIdOnline",
        "GetCharactersCharacterIdLocation",
    ],
)
