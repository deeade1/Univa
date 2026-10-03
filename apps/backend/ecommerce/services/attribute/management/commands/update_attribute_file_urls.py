# ecommerce/services/attribute/management/commands/update_attribute_file_urls.py

"""
DEPRECATED.

This command operated on the old attribute model (file_url column).
That column no longer exists. Rewrite against AttributeValue.value
when needed.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "DEPRECATED — no longer does anything."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "update_attribute_file_urls is deprecated and does nothing."
            )
        )