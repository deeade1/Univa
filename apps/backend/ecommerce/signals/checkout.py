# ecommerce/signals/checkout.py

"""
Checkout signal receivers.

Handles guest → user cart claim on login.
"""

from __future__ import annotations

import logging

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from ecommerce.services.checkout.claim import (
    ClaimError,
    claim_checkout,
)
from ecommerce.services.checkout.lifecycle import (
    get_checkout_by_token,
)

logger = logging.getLogger(__name__)


ANONYMOUS_CHECKOUT_SESSION_KEY = "anonymous_checkout_token"


@receiver(user_logged_in)
def claim_anonymous_checkout_on_login(sender, request, user, **kwargs):
    """
    On successful login, transfer any session-stored anonymous
    checkout to the newly authenticated user.

    The session key is set by `CheckoutSessionMiddleware` (browser
    flow) or by the client directly (JWT flow, which stores the
    token outside the session).

    On successful claim, the session key is cleared. On failure,
    it is left in place so a later attempt can retry.
    """
    if request is None:
        return

    token = request.session.get(ANONYMOUS_CHECKOUT_SESSION_KEY)
    if not token:
        return

    checkout = get_checkout_by_token(token)
    if checkout is None:
        request.session.pop(ANONYMOUS_CHECKOUT_SESSION_KEY, None)
        return

    try:
        claim_checkout(checkout, user)
    except ClaimError as exc:
        logger.warning(
            "Failed to claim anonymous checkout %s for user %s: %s",
            token,
            user.pk,
            exc,
        )
        return

    request.session.pop(ANONYMOUS_CHECKOUT_SESSION_KEY, None)