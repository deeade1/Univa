# core/models/__init__.py

# ---------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------
# These must be defined before any sibling-module imports below,
# because leaf modules (metadata.py, etc.) import from this namespace.
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Model exports
# ---------------------------------------------------------------------

from core.models.region import (  # noqa: F401, E402
    Region,
    RegionLevel,
    RegionTranslation,
)

# ... whatever else your __init__.py had below this line
