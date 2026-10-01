from channels_graphql_ws import GraphqlWsConsumer
from django.urls import re_path

from .consumers import CallConsumer, ChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/$", ChatConsumer.as_asgi()),
    re_path(r"ws/graphql/$", GraphqlWsConsumer.as_asgi()),
    re_path(r'ws/call/$', CallConsumer.as_asgi()),
]