from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import (Call, ChatRoom, Message, MessageReaction, StatusUpdate,
                     StatusView, UserStatus)

User = get_user_model()

class ParticipantsInline(admin.TabularInline):
    model = ChatRoom.participants.through
    extra = 1
    verbose_name = "Participant"
    verbose_name_plural = "Participants"
    raw_id_fields = ('user',)

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ('sender', 'short_text', 'timestamp', 'is_disappearing')
    readonly_fields = ('short_text', 'timestamp')
    
    def short_text(self, obj):
        return obj.text[:50] + "..." if obj.text else ""
    short_text.short_description = "Text Preview"

class ChatRoomAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'room_type',
        'admin_link',
        'participants_count',
        'created_at',
    )
    list_filter = ('room_type', 'created_at')
    search_fields = ('name', 'participants__fist_name')
    raw_id_fields = ('admin',)
    inlines = [ParticipantsInline, MessageInline]
    fieldsets = (
        (None, {
            'fields': (
                'name',
                'room_type',
                'admin',
                'disappearing_messages_duration',
            )
        }),
        ('Media', {
            'fields': ('group_photo',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def admin_link(self, obj):
        if obj.admin:
            url = reverse("admin:accounts_user_change", args=(obj.admin.id,))
            return format_html('<a href="{}">{}</a>', url, obj.admin.username)
        return "-"
    admin_link.short_description = "Admin"

    def participants_count(self, obj):
        return obj.participants.count()
    participants_count.short_description = "Participants"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('participants')

class MessageReactionInline(admin.TabularInline):
    model = MessageReaction
    extra = 0
    raw_id_fields = ('user',)

class MessageAdmin(admin.ModelAdmin):
    list_display = ('short_text', 'chatroom_link', 'sender_link', 'timestamp', 'is_disappearing')
    list_filter = (
        'is_disappearing',
        'timestamp',
        'chatroom__room_type',
    )
    search_fields = ('name', 'participants__first_name')
    raw_id_fields = ('sender', 'reply_to', 'chatroom')
    readonly_fields = ('timestamp', 'disappear_at', 'message_preview')
    inlines = [MessageReactionInline]
    fieldsets = (
        (None, {
            'fields': ('chatroom', 'sender', 'reply_to')
        }),
        ('Content', {
            'fields': ('text', 'image', 'file', 'message_preview')
        }),
        ('Status', {
            'fields': ('is_disappearing', 'disappear_at', 'read_by')
        }),
        ('Timestamps', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )

    def chatroom_link(self, obj):
        url = reverse("admin:chat_chatroom_change", args=(obj.chatroom.id,))
        return format_html('<a href="{}">{}</a>', url, obj.chatroom)
    chatroom_link.short_description = "Chatroom"

    def sender_link(self, obj):
        url = reverse("admin:accounts_user_change", args=(obj.sender.id,))
        return format_html('<a href="{}">{}</a>', url, obj.sender.username)
    sender_link.short_description = "Sender"

    def short_text(self, obj):
        return obj.text[:50] + "..." if obj.text else ""
    short_text.short_description = "Text"

    def message_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 200px;"/>', obj.image.url)
        return "-"
    message_preview.short_description = "Media Preview"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender', 'chatroom', 'reply_to')

class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'message_link', 'user_link', 'reaction', 'created_at')
    list_filter = ('reaction', 'created_at')
    raw_id_fields = ('message', 'user')
    readonly_fields = ('created_at',)

    def message_link(self, obj):
        url = reverse("admin:chat_message_change", args=(obj.message.id,))
        return format_html('<a href="{}">Message #{}</a>', url, obj.message.id)
    message_link.short_description = "Message"

    def user_link(self, obj):
        url = reverse("admin:accounts_user_change", args=(obj.user.id,))
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = "User"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('message', 'user')

class UserStatusAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'online', 'last_seen', 'typing', 'typing_in_link')
    list_filter = ('online', 'typing')
    search_fields = ('user__first_name',)
    raw_id_fields = ('user', 'typing_in')
    readonly_fields = ('last_seen',)

    def user_link(self, obj):
        url = reverse("admin:accounts_user_change", args=(obj.user.id,))
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = "User"

    def typing_in_link(self, obj):
        if obj.typing_in:
            url = reverse("admin:chat_chatroom_change", args=(obj.typing_in.id,))
            return format_html('<a href="{}">{}</a>', url, obj.typing_in)
        return "-"
    typing_in_link.short_description = "Typing In"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'typing_in')

class StatusViewInline(admin.TabularInline):
    model = StatusView
    extra = 0
    raw_id_fields = ('user',)
    readonly_fields = ('viewed_at',)

class StatusUpdateAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'short_text', 'created_at', 'expires_at', 'views_count')
    list_filter = ('created_at', 'expires_at')
    search_fields = ('text', 'user__first_name')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'expires_at', 'media_preview')
    inlines = [StatusViewInline]
    fieldsets = (
        (None, {
            'fields': ('user',)
        }),
        ('Content', {
            'fields': ('text', 'image', 'media_preview')
        }),
        ('Timing', {
            'fields': ('created_at', 'expires_at')
        }),
    )

    def user_link(self, obj):
        url = reverse("admin:accounts_user_change", args=(obj.user.id,))
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = "User"

    def short_text(self, obj):
        return obj.text[:50] + "..." if obj.text else ""
    short_text.short_description = "Text"

    def views_count(self, obj):
        return obj.views.count()
    views_count.short_description = "Views"

    def media_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 200px;"/>', obj.image.url)
        elif obj.video:
            return format_html('<video controls width="250"><source src="{}"></video>', obj.video.url)
        return "-"
    media_preview.short_description = "Media Preview"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('views')

class StatusViewAdmin(admin.ModelAdmin):
    list_display = ('status_link', 'user_link', 'viewed_at')
    list_filter = ('viewed_at',)
    raw_id_fields = ('status', 'user')
    readonly_fields = ('viewed_at',)

    def status_link(self, obj):
        url = reverse("admin:chat_statusupdate_change", args=(obj.status.id,))
        return format_html('<a href="{}">Status #{}</a>', url, obj.status.id)
    status_link.short_description = "Status"

    def user_link(self, obj):
        url = reverse("admin:accounts_user_change", args=(obj.user.id,))
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = "User"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('status', 'user')

class CallAdmin(admin.ModelAdmin):
    list_display = ('caller_link', 'recipient_link', 'call_type', 'status', 'started_at', 'duration_display')
    list_filter = ('call_type', 'status', 'started_at')
    search_fields = ('caller__first_name', 'recipient__first_name')
    raw_id_fields = ('caller', 'recipient')
    readonly_fields = ('started_at', 'ended_at', 'duration_display', 'call_details')
    fieldsets = (
        (None, {
            'fields': ('caller', 'recipient', 'call_type', 'status')
        }),
        ('Timing', {
            'fields': ('started_at', 'ended_at', 'duration_display')
        }),
        ('Technical Details', {
            'fields': ('sdp_offer', 'sdp_answer', 'ice_candidates', 'call_details'),
            'classes': ('collapse',)
        }),
    )

    def caller_link(self, obj):
        url = reverse("admin:accounts_user_change", args=(obj.caller.id,))
        return format_html('<a href="{}">{}</a>', url, obj.caller.username)
    caller_link.short_description = "Caller"

    def recipient_link(self, obj):
        url = reverse("admin:accounts_user_change", args=(obj.recipient.id,))
        return format_html('<a href="{}">{}</a>', url, obj.recipient.username)
    recipient_link.short_description = "Recipient"

    def duration_display(self, obj):
        if obj.started_at and obj.ended_at:
            total_seconds = int(
                (obj.ended_at - obj.started_at).total_seconds()
            )
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours}h {minutes}m {seconds}s"
        return "-"
    duration_display.short_description = "Duration"

    def call_details(self, obj):
        details = []
        if obj.sdp_offer:
            details.append(f"<strong>SDP Offer:</strong> {obj.sdp_offer[:100]}...")
        if obj.sdp_answer:
            details.append(f"<strong>SDP Answer:</strong> {obj.sdp_answer[:100]}...")
        if obj.ice_candidates:
            details.append(f"<strong>ICE Candidates:</strong> {len(obj.ice_candidates)}")
        return mark_safe("<br>".join(details)) if details else "-"
    call_details.short_description = "Call Details"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('caller', 'recipient')

admin.site.register(ChatRoom, ChatRoomAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(MessageReaction, MessageReactionAdmin)
admin.site.register(UserStatus, UserStatusAdmin)
admin.site.register(StatusUpdate, StatusUpdateAdmin)
admin.site.register(StatusView, StatusViewAdmin)
admin.site.register(Call, CallAdmin)
