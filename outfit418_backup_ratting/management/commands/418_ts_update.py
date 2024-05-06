from django.core.management.base import BaseCommand, CommandParser

from allianceauth.services.modules.teamspeak3.models import Teamspeak3User
from allianceauth.services.modules.teamspeak3.tasks import Teamspeak3Tasks


class Command(BaseCommand):
    help = 'Update ts groups for all users or a list of user ids'

    def add_arguments(self, parser: CommandParser):
        parser.add_argument('user_ids', nargs='*', type=int)

    def handle(self, *args, **options):
        if len(options['user_ids']) > 0:
            for pk in options['user_ids']:
                if Teamspeak3User.objects.filter(pk=pk).exists():
                    Teamspeak3Tasks.update_groups.delay(pk)
                    self.stdout.write(self.style.SUCCESS(f'Task scheduled for user with id {pk}'))
                else:
                    self.stdout.write(self.style.WARNING(f'User with id {pk} does not have a TS3 account!'))
        else:
            Teamspeak3Tasks.update_all_groups.delay()
            self.stdout.write(self.style.SUCCESS('Tasks scheduled for all users!'))
