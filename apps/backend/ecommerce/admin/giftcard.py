import json

from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from django_prices.templatetags import prices_i18n

from ecommerce.models.giftCard import GiftCard, GiftCardEvent, GiftCardTag


class GiftCardEventInline(admin.TabularInline):
    model = GiftCardEvent
    extra = 0
    readonly_fields = ('date', 'type_display', 'user_link', 'order_link', 'parameters_display')
    fields = ('date', 'type_display', 'user_link', 'order_link', 'parameters_display')
    can_delete = False
    
    def type_display(self, obj):
        return obj.get_type_display()
    type_display.short_description = _("Type")
    
    def user_link(self, obj):
        if not obj.user:
            return "-"
        url = reverse("admin:accounts_user_change", args=(obj.user.id,))
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = _("User")
    
    def order_link(self, obj):
        if not obj.order:
            return "-"
        url = reverse("admin:order_order_change", args=(obj.order.id,))
        return format_html('<a href="{}">#{}</a>', url, obj.order.number)
    order_link.short_description = _("Order")
    
    def parameters_display(self, obj):
        if not obj.parameters:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.parameters, indent=2))
    parameters_display.short_description = _("Parameters")
    
    def has_add_permission(self, request, obj=None):
        return False



@admin.register(GiftCardTag)
class GiftCardTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'gift_cards_count')
    search_fields = ('name',)
    ordering = ('name',)

    def gift_cards_count(self, obj):
        # Use annotated value if available for better performance
        return getattr(obj, "gift_cards_count", obj.gift_cards.count())
    gift_cards_count.short_description = _("Gift Cards")

    def get_queryset(self, request):
        # Annotate queryset with gift card counts for display efficiency
        qs = super().get_queryset(request)
        return qs.annotate(gift_cards_count=Count('gift_cards'))


@admin.register(GiftCard)
class GiftCardAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'display_balance',
        'initial_balance_display',
        'status',
        'expiry_status',
        'created_by_display',
        'used_by_display',
        'created_at',
        'last_used_on',
    )
    list_filter = (
        'is_active',
        'expiry_date',
        'created_at',
        'currency',
    )
    search_fields = (
        'code',
        'created_by_email',
        'used_by_email',
        'tags__name',
    )
    raw_id_fields = (
        'created_by',
        'used_by',
        'product',
        'fulfillment_line',
    )
    readonly_fields = (
        'created_at',
        'last_used_on',
        'balance_details',
        'events_link',
        'display_code',
    )
    inlines = [GiftCardEventInline]
    fieldsets = (
    (None, {
        'fields': (
            'code',
            'display_code',
            'is_active',
            'tags',
        )
    }),
    ('Balance', {
        'fields': (
            'initial_balance_amount',
            'current_balance_amount',
            'balance_details',
            'currency',
        )
    }),
    ('Dates', {
        'fields': (
            'created_at',
            'expiry_date',
            'last_used_on',
        )
    }),
    ('Ownership', {
        'fields': (
            'created_by',
            'created_by_email',
            'used_by',
            'used_by_email',
        )
    }),
    ('Related', {
        'fields': (
            'product',
            'fulfillment_line',
            'events_link',
        ),
        'classes': ('collapse',)
    }),
)

    actions = ['activate_gift_cards', 'deactivate_gift_cards']
    
    def display_balance(self, obj):
        return prices_i18n.amount(obj.current_balance)
    display_balance.short_description = _("Current Balance")
    display_balance.admin_order_field = 'current_balance_amount'
    
    def initial_balance_display(self, obj):
        return prices_i18n.amount(obj.initial_balance)
    initial_balance_display.short_description = _("Initial Balance")
    initial_balance_display.admin_order_field = 'initial_balance_amount'
    
    def status(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">{}</span>', _("Active"))
        return format_html('<span style="color: red;">{}</span>', _("Inactive"))
    status.short_description = _("Status")
    
    def expiry_status(self, obj):
        if not obj.expiry_date:
            return "-"
        today = timezone.now().date()
        if obj.expiry_date < today:
            return format_html('<span style="color: red;">{}</span>', _("Expired"))
        elif (obj.expiry_date - today).days <= 30:
            return format_html('<span style="color: orange;">{}</span>', _("Expiring Soon"))
        return format_html('<span style="color: green;">{}</span>', _("Valid"))
    expiry_status.short_description = _("Expiry Status")
    
    def created_by_display(self, obj):
        if obj.created_by:
            url = reverse("admin:accounts_user_change", args=(obj.created_by.id,))
            return format_html('<a href="{}">{}</a>', url, obj.created_by.email)
        return obj.created_by_email or "-"
    created_by_display.short_description = _("Created By")
    
    def used_by_display(self, obj):
        if obj.used_by:
            url = reverse("admin:accounts_user_change", args=(obj.used_by.id,))
            return format_html('<a href="{}">{}</a>', url, obj.used_by.email)
        return obj.used_by_email or "-"
    used_by_display.short_description = _("Used By")
    
    def balance_details(self, obj):
        usage_percentage = (
            (obj.initial_balance_amount - obj.current_balance_amount) / 
            obj.initial_balance_amount * 100
        ) if obj.initial_balance_amount else 0
        
        return mark_safe("<br>".join([
            f"<strong>{_('Usage')}:</strong> {usage_percentage:.1f}%",
            f"<strong>{_('Remaining')}:</strong> {prices_i18n.amount(obj.current_balance)}",
            f"<strong>{_('Initial')}:</strong> {prices_i18n.amount(obj.initial_balance)}",
        ]))
    balance_details.short_description = _("Balance Details")
    
    def events_link(self, obj):
        count = obj.events.count()
        url = reverse("admin:giftcard_giftcardevent_changelist") + f"?gift_card__id__exact={obj.id}"
        return format_html('<a href="{}">{} {}</a>', url, count, _("events"))
    events_link.short_description = _("Events")
    
    def activate_gift_cards(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, _("Successfully activated %d gift cards.") % updated)
    activate_gift_cards.short_description = _("Activate selected gift cards")
    
    def deactivate_gift_cards(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, _("Successfully deactivated %d gift cards.") % updated)
    deactivate_gift_cards.short_description = _("Deactivate selected gift cards")
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'created_by',
            'used_by',
            'product',
            'fulfillment_line',
        ).prefetch_related('tags')

@admin.register(GiftCardEvent)
class GiftCardEventAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'gift_card_link',
        'type_display',
        'user_link',
        'order_link',
        'parameters_preview',
    )
    list_filter = (
        'type',
        'date',
    )
    search_fields = (
        'gift_card__code',
        'user__email',
        'order__number',
    )
    raw_id_fields = (
        'user',
        'order',
        'gift_card',
    )
    readonly_fields = (
        'date',
        'type_display',
        'user_link',
        'order_link',
        'gift_card_link',
        'parameters_display',
    )
    fieldsets = (
        (None, {
            'fields': (
                'date',
                'type_display',
                'gift_card_link',
            )
        }),
        ('Related', {
            'fields': (
                'user_link',
                'order_link',
            )
        }),
        ('Details', {
            'fields': ('parameters_display',),
            'classes': ('collapse',)
        }),
    )
    
    def gift_card_link(self, obj):
        url = reverse("admin:giftcard_giftcard_change", args=(obj.gift_card.id,))
        return format_html('<a href="{}">{}</a>', url, obj.gift_card.code)
    gift_card_link.short_description = _("Gift Card")
    
    def type_display(self, obj):
        return obj.get_type_display()
    type_display.short_description = _("Type")
    
    def user_link(self, obj):
        if not obj.user:
            return "-"
        url = reverse("admin:accounts_user_change", args=(obj.user.id,))
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = _("User")
    
    def order_link(self, obj):
        if not obj.order:
            return "-"
        url = reverse("admin:order_order_change", args=(obj.order.id,))
        return format_html('<a href="{}">#{}</a>', url, obj.order.number)
    order_link.short_description = _("Order")
    
    def parameters_preview(self, obj):
        if not obj.parameters:
            return "-"
        preview = ", ".join(f"{k}: {v}" for k, v in list(obj.parameters.items())[:3])
        if len(obj.parameters) > 3:
            preview += "..."
        return preview
    parameters_preview.short_description = _("Parameters")
    
    def parameters_display(self, obj):
        if not obj.parameters:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.parameters, indent=2))
    parameters_display.short_description = _("Parameters Details")
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'gift_card',
            'user',
            'order',
        )