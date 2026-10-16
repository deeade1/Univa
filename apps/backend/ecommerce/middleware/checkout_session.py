# ecommerce/middleware/checkout_session.py

"""
Session persistence for anonymous checkout tokens.

GraphQL clients that create a checkout via `checkoutCreate` receive
a token. This middleware reads the GraphQL response body and stores
that token in the Django session so the `user_logged_in` signal can
auto-claim the cart on next login.

Scope
-----

Only `checkoutCreate` responses are inspected. Every other GraphQL
request passes through untouched — no JSON parsing, no overhead.

Clients that don't use Django sessions (mobile apps, SPAs with JWT)
skip this entirely and call the `checkoutClaim` mutation explicitly.
"""

from __future__ import annotations

import json
import logging

from django.utils.deprecation import MiddlewareMixin


logger = logging.getLogger(__name__)


ANONYMOUS_CHECKOUT_SESSION_KEY = "anonymous_checkout_token"

# Only inspect responses whose body we expect to carry a checkout
# token. Any other response passes through unmodified.
_TOKEN_MUTATIONS = ("checkoutCreate",)


class CheckoutSessionMiddleware(MiddlewareMixin):
    """
    Store the anonymous checkout token in the session when
    `checkoutCreate` returns one.
    """

    def process_response(self, request, response):
        if not hasattr(request, "session"):
            return response

        content_type = response.get("Content-Type", "")
        if "application/json" not in content_type:
            return response

        try:
            payload = json.loads(response.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return response

        token = self._extract_checkout_token(payload)
        if not token:
            return response

        request.session[ANONYMOUS_CHECKOUT_SESSION_KEY] = token

        # ↓↓↓ THE LOG LINE GOES HERE ↓↓↓
        logger.info(
            "Stored anonymous checkout token %s in session %s",
            token,
            request.session.session_key,
        )
        # ↑↑↑ THE LOG LINE GOES HERE ↑↑↑

        return response
    
    def _extract_checkout_token(self, payload):
        """
        Walk the response payload and return the token from the
        first `checkoutCreate` mutation result, if any.

        Expected shape:

            {"data": {"checkoutCreate": {"checkout": {"token": "..."}}}}
        """
        if not isinstance(payload, dict):
            return None

        data = payload.get("data")
        if not isinstance(data, dict):
            return None

        for name in _TOKEN_MUTATIONS:
            result = data.get(name)
            if not isinstance(result, dict):
                continue

            checkout = result.get("checkout")
            if not isinstance(checkout, dict):
                continue

            token = checkout.get("token")
            if token:
                return str(token)

        return None