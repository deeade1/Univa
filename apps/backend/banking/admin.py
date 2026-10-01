from django.contrib import admin
from django.utils import timezone
from django.db.models import Sum
from .models import (
    # Core Models
    Bank, Account,
    
    # Payment Models
    Transaction, MoneyTransfer, BillPayment, AirtimePurchase, PaymentStat,
    
    # Accounting Models
    LedgerEntry, AccountingJournal, FloatAccount,
    
    # Compliance Models
    ATMCard, ATMTransaction, CardIssuance, Contact,
    CurrencyExchangeRate, Webhook, WebhookDelivery,
    
    # Regulatory Models
    BVNVerification, CBNReport,
    
    # Security Models
    PhoneChangeRequest, FraudDetectionRule, FraudAlert, AuditLog,
    
    # Integration Models
    BankAPIIntegration, APITransactionLog,
    
    # Reconciliation Models
    ReconciliationRun, ReconciliationMatch, UnreconciledTransaction,
    
    # NEW: OPay Features
    QRCode, QRTransaction,
    Merchant, MerchantTransaction,
    SavingsGoal, SavingsTransaction, AutoSaveRule,
)


@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'is_partner_bank', 'virtual_account_provider']
    list_filter = ['is_active', 'is_partner_bank', 'virtual_account_provider']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']



@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = [
        'phone_number',
        'account_name',
        'nuban_number',
        'status',
        'created_at',
    ]

    list_filter = [
        'status',
    ]

    search_fields = [
        'phone_number',
        'nuban_number',
        'account_name',
        'user__user__email',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
    ]

    raw_id_fields = ['user', 'bank']

    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'phone_number', 'nuban_number', 'bank', 'account_name')
        }),
        ('Security', {
            'fields': ('pin_hash', 'bvn_hash')
        }),
        ('Status & Limits', {
            'fields': ('status', 'daily_limit', 'single_transaction_limit')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'reference',
        'account',
        'amount',
        'type',
        'status',
        'created_at',
    ]

    list_filter = [
        'type',
        'status',
        'created_at',
    ]

    search_fields = [
        'reference',
        'account__phone_number',
        'narration',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
    ]

    raw_id_fields = ['account']

    fieldsets = (
        ('Transaction Details', {
            'fields': ('reference', 'account', 'type', 'amount', 'status')
        }),
        ('Recipient (Transfers Only)', {
            'fields': (
                'recipient_phone',
                'recipient_name',
                'recipient_bank_code',
                'recipient_account_number',
            )
        }),
        ('Additional Info', {
            'fields': ('narration', 'fee', 'balance_after', 'provider_reference')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )



@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'merchant_id', 'user', 'verification_status', 'is_active', 'created_at']
    list_filter = ['verification_status', 'is_active', 'business_type']
    search_fields = ['business_name', 'merchant_id', 'business_email', 'business_phone']
    readonly_fields = ['merchant_id', 'created_at', 'updated_at']
    raw_id_fields = ['user', 'settlement_account', 'settlement_bank']
    
    fieldsets = (
        ('Business Information', {
            'fields': ('user', 'business_name', 'business_type', 'business_registration_number')
        }),
        ('Contact Details', {
            'fields': ('business_email', 'business_phone', 'business_address', 'business_city', 'business_state')
        }),
        ('Financial', {
            'fields': ('settlement_account', 'settlement_bank', 'transaction_fee_percentage')
        }),
        ('Status', {
            'fields': ('verification_status', 'is_active', 'verified_at')
        }),
        ('Statistics', {
            'fields': ('total_transactions', 'total_volume', 'successful_transactions')
        }),
    )


@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    list_display = ['qr_id', 'creator', 'qr_type', 'fixed_amount', 'is_active', 'expires_at', 'created_at']
    list_filter = ['qr_type', 'is_active', 'created_at']
    search_fields = ['qr_id', 'creator__user__email', 'description']
    readonly_fields = ['qr_id', 'created_at', 'updated_at', 'last_used_at']
    raw_id_fields = ['creator', 'merchant']
    
    fieldsets = (
        ('QR Details', {
            'fields': ('qr_id', 'creator', 'merchant', 'qr_type', 'description')
        }),
        ('Payment', {
            'fields': ('fixed_amount', 'max_amount_per_use')
        }),
        ('Usage', {
            'fields': ('max_uses', 'current_uses', 'last_used_at')
        }),
        ('Validity', {
            'fields': ('is_active', 'expires_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'current_amount', 'target_amount', 'progress_percentage', 'is_active', 'is_completed']
    list_filter = ['goal_type', 'is_active', 'is_completed', 'savings_method']
    search_fields = ['name', 'goal_id', 'user__user__email', 'description']
    readonly_fields = ['goal_id', 'created_at', 'updated_at', 'progress_percentage', 'days_remaining']
    raw_id_fields = ['user', 'source_account']
    
    fieldsets = (
        ('Goal Details', {
            'fields': ('goal_id', 'user', 'name', 'description', 'goal_type')
        }),
        ('Target & Progress', {
            'fields': ('target_amount', 'current_amount', 'start_date', 'target_date')
        }),
        ('Savings Method', {
            'fields': ('savings_method', 'fixed_amount', 'percentage', 'round_up_multiplier', 'frequency')
        }),
        ('Auto-save', {
            'fields': ('is_auto_save', 'next_auto_save', 'last_auto_save')
        }),
        ('Status', {
            'fields': ('is_active', 'is_completed', 'is_locked', 'completed_at')
        }),
        ('Calculated Fields', {
            'fields': ('progress_percentage', 'days_remaining', 'daily_savings_needed')
        }),
    )


@admin.register(CardIssuance)
class CardIssuanceAdmin(admin.ModelAdmin):
    list_display = (
        'card',
        'request_type',
        'status',
        'estimated_delivery',
        'fee_paid',
        'created_at',
    )
    list_filter = ('status', 'request_type', 'fee_paid')
    search_fields = (
        'tracking_number',
        'card__card_number',
        'card__user__email',
    )
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('card',)

    fieldsets = (
        ('Issuance Details', {
            'fields': ('card', 'request_type', 'delivery_address')
        }),
        ('Delivery Status', {
            'fields': ('status', 'tracking_number', 'estimated_delivery', 'actual_delivery')
        }),
        ('Fees & Activation', {
            'fields': ('fee', 'fee_paid', 'activation_code', 'activated_at')
        }),
        ('System', {
            'fields': ('created_at', 'updated_at')
        }),
    )



# Register other models with basic admin
admin.site.register(MoneyTransfer)
admin.site.register(BillPayment)
admin.site.register(AirtimePurchase)
admin.site.register(PaymentStat)
admin.site.register(LedgerEntry)
admin.site.register(AccountingJournal)
admin.site.register(FloatAccount)
admin.site.register(ATMCard)
admin.site.register(ATMTransaction)
admin.site.register(Contact)
admin.site.register(CurrencyExchangeRate)
admin.site.register(Webhook)
admin.site.register(WebhookDelivery)
admin.site.register(BVNVerification)
admin.site.register(CBNReport)
admin.site.register(PhoneChangeRequest)
admin.site.register(FraudDetectionRule)
admin.site.register(FraudAlert)
admin.site.register(AuditLog)
admin.site.register(BankAPIIntegration)
admin.site.register(APITransactionLog)
admin.site.register(ReconciliationRun)
admin.site.register(ReconciliationMatch)
admin.site.register(UnreconciledTransaction)
admin.site.register(QRTransaction)
admin.site.register(MerchantTransaction)
admin.site.register(SavingsTransaction)
admin.site.register(AutoSaveRule)