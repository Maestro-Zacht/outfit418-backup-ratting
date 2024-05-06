from django.apps import AppConfig


class Outfit418BackupRattingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'outfit418_backup_ratting'

    def ready(self):
        import outfit418_backup_ratting.signals
