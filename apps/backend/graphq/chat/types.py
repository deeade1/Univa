import graphene
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django_filters import (
    BooleanFilter,
    CharFilter,
    DateTimeFilter,
    FilterSet,
    NumberFilter,
)
from graphene import Node, relay
from graphene_django import DjangoObjectType

from chat.models import (
    Call, ChatRoom, Message,
    MessageReaction, UserStatus, StatusUpdate, StatusView,
)
# ============================================================
# Custom Filter Classes
# ============================================================

class ChatRoomFilter(FilterSet):
    name_contains = CharFilter(field_name="name", lookup_expr="icontains")
    participant_count = NumberFilter(method="filter_participant_count")
    has_unread = BooleanFilter(method="filter_has_unread")

    # Custom filter that maps is_group -> room_type__in
    is_group = BooleanFilter(method="filter_is_group")

    class Meta:
        model = ChatRoom
        fields = {
            "name": ["exact", "icontains", "istartswith"],
            "room_type": ["exact", "in"],
            "created_at": ["exact", "gt", "gte", "lt", "lte"],
            "admin__first_name": ["exact"],
        }
        

    def filter_is_group(self, queryset, name, value):
        group_types = [
            ChatRoomType.GROUP,
            ChatRoomType.TRIP,
            ChatRoomType.DELIVERY,
        ]
        if value:
            return queryset.filter(room_type__in=group_types)
        return queryset.exclude(room_type__in=group_types)

    def filter_participant_count(self, queryset, name, value):
        return queryset.annotate(
            participant_count=models.Count("participants")
        ).filter(participant_count=value)

    def filter_has_unread(self, queryset, name, value):
        user = self.request.user
        if value:
            return queryset.filter(
                messages__read_by__isnull=True
            ).exclude(messages__sender=user)
        return queryset


class MessageFilter(FilterSet):
    text_search = CharFilter(field_name="text", lookup_expr="search")
    has_media = BooleanFilter(method="filter_has_media")
    unread_by_me = BooleanFilter(method="filter_unread_by_me")

    class Meta:
        model = Message
        fields = {
            "text": ["exact", "icontains", "istartswith"],
            "sender__first_name": ["exact"],
            "chatroom__id": ["exact"],
            "timestamp": ["exact", "gt", "gte", "lt", "lte"],
            "is_disappearing": ["exact"],
        }

    def filter_has_media(self, queryset, name, value):
        if value:
            return queryset.exclude(
                models.Q(image="") | models.Q(image__isnull=True)
            )
        return queryset.filter(
            models.Q(image="") | models.Q(image__isnull=True)
        )

    def filter_unread_by_me(self, queryset, name, value):
        user = self.request.user
        if value:
            return queryset.exclude(read_by=user)
        return queryset.filter(read_by=user)


class MessageReactionFilter(FilterSet):
    class Meta:
        model = MessageReaction
        fields = {
            "reaction": ["exact"],
            "user__first_name": ["exact"],
            "message__id": ["exact"],
            "created_at": ["exact", "gt", "gte", "lt", "lte"],
        }


class UserStatusFilter(FilterSet):
    online_since = DateTimeFilter(method="filter_online_since")

    class Meta:
        model = UserStatus
        fields = {
            "online": ["exact"],
            "user__first_name": ["exact"],
            "typing": ["exact"],
            "typing_in__id": ["exact"],
        }

    def filter_online_since(self, queryset, name, value):
        return queryset.filter(online=True, last_seen__gte=value)


class StatusUpdateFilter(FilterSet):
    active_only = BooleanFilter(method="filter_active_only")
    media_type = CharFilter(method="filter_media_type")

    class Meta:
        model = StatusUpdate
        fields = {
            "user__first_name": ["exact"],
            "created_at": ["exact", "gt", "gte", "lt", "lte"],
            "expires_at": ["exact", "gt", "gte", "lt", "lte"],
        }

    def filter_active_only(self, queryset, name, value):
        if value:
            return queryset.filter(expires_at__gt=timezone.now())
        return queryset

    def filter_media_type(self, queryset, name, value):
        if value == "has_media":
            return queryset.exclude(
                models.Q(image="") | models.Q(image__isnull=True)
            )
        return queryset


class StatusViewFilter(FilterSet):
    class Meta:
        model = StatusView
        fields = {
            "status__id": ["exact"],
            "user__first_name": ["exact"],
            "viewed_at": ["exact", "gt", "gte", "lt", "lte"],
        }


class CallFilter(FilterSet):
    duration_min = NumberFilter(method="filter_duration_min")
    duration_max = NumberFilter(method="filter_duration_max")

    class Meta:
        model = Call
        fields = {
            "call_type": ["exact"],
            "status": ["exact"],
            "caller__first_name": ["exact"],
            "recipient__first_name": ["exact"],
            "started_at": ["exact", "gt", "gte", "lt", "lte"],
            "ended_at": ["exact", "gt", "gte", "lt", "lte"],
            "created_at": ["exact", "gt", "gte", "lt", "lte"],
        }

    def _annotate_duration(self, queryset):
        return queryset.annotate(
            _call_duration=models.ExpressionWrapper(
                models.F("ended_at") - models.F("started_at"),
                output_field=models.DurationField(),
            )
        )

    def filter_duration_min(self, queryset, name, value):
        # value is treated as seconds
        return self._annotate_duration(queryset).filter(
            _call_duration__gte=timedelta(seconds=value)
        )

    def filter_duration_max(self, queryset, name, value):
        return self._annotate_duration(queryset).filter(
            _call_duration__lte=timedelta(seconds=value)
        )


# ============================================================
# Node Definitions
# ============================================================

class MessageReactionNode(DjangoObjectType):
    class Meta:
        model = MessageReaction
        fields = "__all__"
        filterset_class = MessageReactionFilter
        interfaces = (relay.Node,)


class ChatRoomNode(DjangoObjectType):
    unread_count = graphene.Int()
    participant_count = graphene.Int()

    class Meta:
        model = ChatRoom
        fields = "__all__"
        filterset_class = ChatRoomFilter
        interfaces = (relay.Node,)

    def resolve_unread_count(self, info):
        user = info.context.user
        if user.is_authenticated:
            return self.messages.exclude(read_by=user).count()
        return 0

    def resolve_participant_count(self, info):
        return self.participants.count()


class MessageNode(DjangoObjectType):
    reactions = graphene.List(MessageReactionNode)
    is_expired = graphene.Boolean()
    is_read_by_me = graphene.Boolean()

    class Meta:
        model = Message
        fields = "__all__"
        filterset_class = MessageFilter
        interfaces = (relay.Node,)

    def resolve_id(self, info):
        return str(self.id)

    def resolve_reactions(self, info):
        return self.reactions.all()

    def resolve_is_expired(self, info):
        if self.is_disappearing and self.disappear_at:
            return timezone.now() > self.disappear_at
        return False

    def resolve_is_read_by_me(self, info):
        user = info.context.user
        if user.is_authenticated:
            return self.read_by.filter(id=user.id).exists()
        return False


class UserStatusNode(DjangoObjectType):
    online_duration = graphene.String()

    class Meta:
        model = UserStatus
        fields = "__all__"
        filterset_class = UserStatusFilter
        interfaces = (relay.Node,)

    def resolve_online_duration(self, info):
        if self.online and self.last_seen:
            return str(timezone.now() - self.last_seen)
        return None


class StatusUpdateNode(DjangoObjectType):
    is_expired = graphene.Boolean()
    view_count = graphene.Int()
    has_viewed = graphene.Boolean()
    media_url = graphene.String()

    class Meta:
        model = StatusUpdate
        fields = "__all__"
        filterset_class = StatusUpdateFilter
        interfaces = (relay.Node,)

    def resolve_id(self, info):
        return str(self.id)

    def resolve_is_expired(self, info):
        return timezone.now() > self.expires_at

    def resolve_view_count(self, info):
        return self.views.count()

    def resolve_has_viewed(self, info):
        user = info.context.user
        if user.is_authenticated:
            return self.views.filter(user=user).exists()
        return False

    def resolve_media_url(self, info):
        if self.image:
            return info.context.build_absolute_uri(self.image.url)
        return None


class StatusViewNode(DjangoObjectType):
    class Meta:
        model = StatusView
        fields = "__all__"
        filterset_class = StatusViewFilter
        interfaces = (relay.Node,)


class CallNode(DjangoObjectType):
    call_duration = graphene.String()

    class Meta:
        model = Call
        fields = "__all__"
        filterset_class = CallFilter
        interfaces = (relay.Node,)

    def resolve_id(self, info):
        return str(self.id)

    def resolve_call_duration(self, info):
        if self.started_at and self.ended_at:
            return str(self.ended_at - self.started_at)
        return None


