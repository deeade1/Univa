from django.core.management.base import BaseCommand
from django.template.defaultfilters import pluralize

from univa_jwt.blacklist import Blacklist
from univa_jwt.models import RefreshToken


class Command(BaseCommand):
    help = "Manage JWT refresh tokens: blacklist revoked tokens or clear tokens."

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='command', help='Sub-command to run')

        # Sub-command: blacklist revoked tokens
        blacklist_parser = subparsers.add_parser('blacklist', help='Blacklist all revoked tokens')

        # Sub-command: clear tokens
        clear_parser = subparsers.add_parser('clear', help='Clear refresh tokens')
        clear_parser.add_argument(
            "--expired",
            action="store_true",
            help="Clear only expired tokens",
        )

    def handle(self, *args, **options):
        command = options.get('command')

        if command == 'blacklist':
            self.blacklist_revoked_tokens()
        elif command == 'clear':
            self.clear_tokens(expired=options.get('expired', False))
        else:
            self.stdout.write(self.style.ERROR("Please specify a valid sub-command: 'blacklist' or 'clear'"))

    def blacklist_revoked_tokens(self):
        revoked_tokens = RefreshToken.objects.filter(revoked__isnull=False)

        for token in revoked_tokens.iterator():
            Blacklist.set(token)

        count = revoked_tokens.count()
        self.stdout.write(self.style.SUCCESS(
            f"Successfully blacklisted {count} token{pluralize(count)}"
        ))

    def clear_tokens(self, expired=False):
        queryset = RefreshToken.objects.expired() if expired else RefreshToken.objects

        deleted_count, _ = queryset.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Successfully deleted {deleted_count} token{pluralize(deleted_count)}"
        ))
