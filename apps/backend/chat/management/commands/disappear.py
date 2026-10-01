from django.core.management.base import BaseCommand
from django.utils import timezone

from .models import Message, StatusUpdate


class Command(BaseCommand):
    help = 'Deletes expired content (disappearing messages and status updates)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--content-type',
            type=str,
            choices=['all', 'messages', 'statuses'],
            default='all',
            help='Specify which content type to clean (all, messages, or statuses)'
        )

    def handle(self, *args, **options):
        content_type = options['content_type']
        total_messages_deleted = 0
        total_statuses_deleted = 0

        # Process disappearing messages if requested
        if content_type in ['all', 'messages']:
            expired_messages = Message.objects.filter(
                is_disappearing=True,
                disappear_at__lte=timezone.now()
            )
            message_count = expired_messages.count()
            expired_messages.delete()
            total_messages_deleted = message_count
            self.stdout.write(self.style.SUCCESS(f'Deleted {message_count} expired messages'))

        # Process status updates if requested
        if content_type in ['all', 'statuses']:
            expired_statuses = StatusUpdate.objects.filter(
                expires_at__lte=timezone.now()
            )
            status_count = expired_statuses.count()
            expired_statuses.delete()
            total_statuses_deleted = status_count
            self.stdout.write(self.style.SUCCESS(f'Deleted {status_count} expired status updates'))

        # Summary if processing all content types
        if content_type == 'all':
            self.stdout.write(self.style.SUCCESS(
                f'Cleanup complete. Removed {total_messages_deleted} messages and {total_statuses_deleted} statuses'
            ))