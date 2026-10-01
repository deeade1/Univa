# apps/backend/accounts/tasks/verification.py

from .email import send_verification_email

__all__ = [
    "send_verification_email",
]