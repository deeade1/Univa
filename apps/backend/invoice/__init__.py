# apps/backend/invoice/__init__.py

# Package initializer for the invoice app.
#
# Intentionally empty. The public API of this package is:
#
#   - invoice.models          — canonical invoice models
#   - invoice.enums           — InvoiceStatus, InvoiceEventType, etc.
#   - invoice.services        — generation, lifecycle, payments, etc.
#
# Do not add domain code here. Anything in this file runs on
# every `import invoice`, including during migrations and
# management command startup.