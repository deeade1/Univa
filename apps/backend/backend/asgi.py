# apps/backend/backend/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.dev")
django.setup()

from graphq.subscriptions.consumers import GraphqlSubscriptionConsumer
from univa_jwt.schema.websocket import WebSocketAuthMiddleware

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        WebSocketAuthMiddleware(
            URLRouter([
                path("graphql/", GraphqlSubscriptionConsumer.as_asgi()),
            ])
        )
    ),
})