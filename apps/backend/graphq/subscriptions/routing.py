# apps/backend/graphq/subscriptions/routing.py
from django.urls import path
from .consumers import GraphqlSubscriptionConsumer

websocket_urlpatterns = [
    path("graphql", GraphqlSubscriptionConsumer.as_asgi()),
]
