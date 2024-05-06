from django.core.management.base import BaseCommand

from outfit418_backup_ratting.tasks import update_all_characters_logins


class Command(BaseCommand):
    help = 'Update login data for all characters'

    def handle(self, *args, **options):
        update_all_characters_logins.delay(True)
        self.stdout.write(self.style.SUCCESS('Tasks scheduled!'))
