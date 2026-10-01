# apps/backend/accounts/models/__init__.py

from .address import Address
from .auth import MagicLoginToken
from .profile import UserProfile
from .role import Role, UserRole
from .user import User

__all__ = [
    "Address",
    "MagicLoginToken",
    "UserProfile",
    "Role",
    "UserRole",
    "User",
]