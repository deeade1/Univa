from django.core.management.base import BaseCommand
from django.template.defaultfilters import pluralize

from univa_jwt.models import RefreshToken


class Command(BaseCommand):
    help = "Clears refresh tokens"

    def add_arguments(self, parser):
        parser.add_argument(
            "--expired",
            action="store_true",
            help="Clears expired tokens",
        )

    def handle(self, expired, *args, **options):
        qs = RefreshToken.objects
        if expired:
            qs = qs.expired().filter(expired=True)

        deleted, _ = qs.all().delete()

        msg = "Successfully deleted {} token{}".format(deleted, pluralize(deleted))

        self.stdout.write(self.style.SUCCESS(msg))
