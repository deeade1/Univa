# apps/backend/ecommerce/models/constants.py

"""
DEPRECATED MODULE PATH.

Enums now live in `ecommerce.models.enums`.

This module is kept as a thin re-export shim so that existing
imports of the form:

    from ecommerce.models.constants import ProductTypeKind

continue to work during the refactor.

New code should import from `ecommerce.models.enums` directly:

    from ecommerce.models.enums import ProductTypeKind

This shim will be deleted once all imports are migrated.
"""

from ecommerce.models.enums import *  # noqa: F401,F403
from ecommerce.models.enums import __all__  # noqa: F401