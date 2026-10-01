"""
JWT lifecycle signals.
"""

from django.dispatch import Signal


refresh_token_created = Signal()

refresh_token_revoked = Signal()

refresh_token_rotated = Signal()

refresh_finished = Signal()