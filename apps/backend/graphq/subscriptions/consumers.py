import logging
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
import channels_graphql_ws
from backend.schema import schema
from univa_jwt.schema.websocket import WebSocketAuthMiddleware

logger = logging.getLogger(__name__)


class GraphqlSubscriptionConsumer(channels_graphql_ws.GraphqlWsConsumer):
    """
    GraphQL WebSocket consumer that:
    - reads `connection_init` payload (graphql-ws / apollo-link-ws style)
    - tries to authenticate the token from payload (preferred)
    - falls back to whatever `scope['user']` already contains (middleware)
    - exposes ASGI scope to resolvers as info.context.channels_scope
    """

    schema = schema

    async def on_connect(self, payload):
        """
        Called by channels-graphql-ws when client sends connection_init.
        `payload` is the connection_init payload (connectionParams).
        """
        logger.info("=" * 60)
        logger.info("🔌 WebSocket CONNECT — received connection_init payload:")
        logger.info(f"📦 payload: {payload!r}")

        # Preserve raw payload in scope for later debugging/inspection
        if payload and isinstance(payload, dict):
            self.scope["connection_params"] = payload
            logger.info("📦 Stored connection_params in scope")

        # Start with middleware-provided user if available
        current_user = self.scope.get("user", None) or AnonymousUser()

        # Try to extract token from payload first (highest priority)
        token = None
        try:
            if payload and isinstance(payload, dict):
                # Common shapes:
                # { authorization: "Bearer <token>" }
                # { headers: { authorization: "Bearer <token>" } }
                # { token: "<token>" }
                token = payload.get("authorization") or payload.get("Authorization")
                if not token:
                    headers = payload.get("headers") or {}
                    token = headers.get("authorization") or headers.get("Authorization")
                if not token:
                    token = payload.get("token")

            # Normalize "Bearer <token>" to raw token
            raw_token = None
            if token and isinstance(token, str):
                if token.startswith("Bearer "):
                    raw_token = token.split(" ", 1)[1]
                else:
                    raw_token = token

            # If we have a token, use your existing auth helper to resolve user
            if raw_token:
                # call the sync auth helper through database_sync_to_async
                # Note: get_user_from_any_token is an instance method, call it on a helper instance
                auth_mw = WebSocketAuthMiddleware(lambda s, r, se: None)
                user_obj = await database_sync_to_async(auth_mw.get_user_from_any_token)(raw_token)

                if user_obj and getattr(user_obj, "is_authenticated", False):
                    self.scope["user"] = user_obj
                    current_user = user_obj
                    logger.info("🔐 Authenticated user from connection_init payload")
                else:
                    logger.info("🔒 Token present but did not authenticate to a user")
        except Exception as e:
            logger.exception("⚠️ on_connect: token parsing/auth failed: %s", e)

        # Fallback: if middleware already set user earlier (querystring/header), preserve it
        if not getattr(current_user, "is_authenticated", False):
            middleware_user = self.scope.get("user", None)
            if middleware_user and getattr(middleware_user, "is_authenticated", False):
                current_user = middleware_user

        # Log final decision
        if current_user and getattr(current_user, "is_authenticated", False):
            logger.info(f"🎉 WebSocket authenticated as: {getattr(current_user, 'email', repr(current_user))}")
        else:
            logger.warning("🚫 WebSocket connection is anonymous")

        logger.info("Scope summary keys: %s", list(self.scope.keys()))
        logger.info("=" * 60)

        # Call parent (accepts the connection)
        await super().on_connect(payload)

    async def disconnect(self, code):
        logger.info(f"🔌 WebSocket DISCONNECT → code={code}")
        await super().disconnect(code)

    async def get_context(self, request=None):
        """
        channels-graphql-ws expects you to return the GraphQL context here.
        We expose the ASGI scope under 'channels_scope' so resolvers can access
        user and other scope items consistently for WebSocket operations.
        """
        user = self.scope.get("user", AnonymousUser())
        logger.info(f"🔌 get_context → user: {user if getattr(user, 'is_authenticated', False) else 'Anonymous'}")
        return {"channels_scope": self.scope}
