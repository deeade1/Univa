# apps/backend/univa_jwt/constants.py

"""
Constants used by the Univa JWT subsystem.
"""

from typing import Final


# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------

ACCESS_TOKEN: Final[str] = "access"
REFRESH_TOKEN: Final[str] = "refresh"


# ---------------------------------------------------------------------------
# JWT claims
# ---------------------------------------------------------------------------

CLAIM_SUBJECT: Final[str] = "sub"
CLAIM_TOKEN_TYPE: Final[str] = "token_type"
CLAIM_JTI: Final[str] = "jti"
CLAIM_ISSUER: Final[str] = "iss"
CLAIM_AUDIENCE: Final[str] = "aud"
CLAIM_ISSUED_AT: Final[str] = "iat"
CLAIM_EXPIRATION: Final[str] = "exp"


# ---------------------------------------------------------------------------
# Authentication scheme
# ---------------------------------------------------------------------------

AUTH_SCHEME_BEARER: Final[str] = "Bearer"


# ---------------------------------------------------------------------------
# Refresh-token state
# ---------------------------------------------------------------------------

REFRESH_ACTIVE: Final[str] = "active"
REFRESH_REVOKED: Final[str] = "revoked"
REFRESH_EXPIRED: Final[str] = "expired"
REFRESH_ROTATED: Final[str] = "rotated"


# ---------------------------------------------------------------------------
# Token sources
# ---------------------------------------------------------------------------

TOKEN_SOURCE_HTTP: Final[str] = "http"
TOKEN_SOURCE_WEBSOCKET: Final[str] = "websocket"
TOKEN_SOURCE_GRAPHQL: Final[str] = "graphql"