# ecommerce/signals/__init__.py

"""
Signal registration for the ecommerce app.

Importing this module is what registers all ecommerce signal
handlers. It is imported from EcommerceConfig.ready().
"""

from ecommerce.signals import order  # noqa: F401