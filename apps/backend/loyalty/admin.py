# apps/backend/loyalty/admin.py

from django.contrib import admin
from django.utils import timezone


from loyalty.models.history import LoyaltyHistory
from loyalty.models.reward import LoyaltyReward
from loyalty.models.tier import LoyaltyRewardTier



class LoyaltyHistoryInline(admin.TabularInline):
    """Inline for LoyaltyHistory in User admin."""
    model = LoyaltyHistory
    extra = 0
    fields = ("reward", "date_redeemed")
    readonly_fields = ("date_redeemed",)
    max_num = 10
    can_delete = False
    show_change_link = True


class LoyaltyRewardInline(admin.TabularInline):
    """Inline for LoyaltyReward in User admin."""
    model = LoyaltyReward
    extra = 0
    fields = ("reward_type", "discount_percent", "expires", "created_at")
    readonly_fields = ("created_at",)
    max_num = 5


@admin.register(LoyaltyRewardTier)
class LoyaltyRewardTierAdmin(admin.ModelAdmin):
    list_display = ("points_needed", "reward", "description", "active")
    list_filter = ("active",)
    search_fields = ("reward", "description")
    ordering = ("points_needed",)
    list_editable = ("reward", "description", "active")
    actions = ["activate_tiers", "deactivate_tiers"]
    
    def activate_tiers(self, request, queryset):
        queryset.update(active=True)
        self.message_user(request, f"{queryset.count()} tier(s) activated.")
    activate_tiers.short_description = "Activate selected tiers"
    
    def deactivate_tiers(self, request, queryset):
        queryset.update(active=False)
        self.message_user(request, f"{queryset.count()} tier(s) deactivated.")
    deactivate_tiers.short_description = "Deactivate selected tiers"


@admin.register(LoyaltyHistory)
class LoyaltyHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "reward", "date_redeemed")
    list_filter = ("date_redeemed",)
    search_fields = ("user__email", "reward")
    readonly_fields = ("date_redeemed",)
    ordering = ("-date_redeemed",)
    date_hierarchy = "date_redeemed"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user")
    
    def has_add_permission(self, request):
        # Prevent manual creation
        return False


@admin.register(LoyaltyReward)
class LoyaltyRewardAdmin(admin.ModelAdmin):
    list_display = ("user", "reward_type", "discount_percent", "expires", "is_expired", "created_at")
    list_filter = ("reward_type", "expires")
    search_fields = ("user__user__email", "reward_type")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_editable = ("discount_percent",)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user", "user__user")
    
    def is_expired(self, obj):
        return obj.expires < timezone.now()
    is_expired.boolean = True
    is_expired.short_description = "Expired"
    
    def has_add_permission(self, request):
        # Prevent manual creation
        return False