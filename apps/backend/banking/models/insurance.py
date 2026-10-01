# apps/backend/banking/models/insurance.py

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


MONEY_QUANTUM = Decimal("0.01")


class InsuranceProvider(models.Model):
    """Insurance companies"""

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    logo = models.ImageField(
        upload_to='insurance_providers/', blank=True, null=True
    )
    website = models.URLField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class InsuranceProduct(models.Model):
    """Insurance products offered"""

    INSURANCE_TYPES = [
        ('MOTOR', 'Motor Insurance'),
        ('HEALTH', 'Health Insurance'),
        ('LIFE', 'Life Insurance'),
        ('TRAVEL', 'Travel Insurance'),
        ('PROPERTY', 'Property Insurance'),
        ('DEVICE', 'Device Insurance'),
        ('AGRICULTURE', 'Agriculture Insurance'),
        ('EDUCATION', 'Education Insurance'),
        ('OTHER', 'Other'),
    ]

    PAYMENT_FREQUENCIES = [
        ('ONE_TIME', 'One Time'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('ANNUALLY', 'Annually'),
    ]

    provider = models.ForeignKey(
        InsuranceProvider,
        on_delete=models.PROTECT,
        related_name='products',
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    insurance_type = models.CharField(max_length=20, choices=INSURANCE_TYPES)
    description = models.TextField()

    coverage_details = models.JSONField(default=dict)
    exclusions = models.JSONField(default=list)
    coverage_amount_min = models.DecimalField(max_digits=15, decimal_places=2)
    coverage_amount_max = models.DecimalField(max_digits=15, decimal_places=2)

    premium_min = models.DecimalField(max_digits=10, decimal_places=2)
    premium_max = models.DecimalField(max_digits=10, decimal_places=2)
    payment_frequency = models.CharField(
        max_length=20, choices=PAYMENT_FREQUENCIES
    )

    min_tenure_months = models.IntegerField()
    max_tenure_months = models.IntegerField()
    default_tenure_months = models.IntegerField()

    required_documents = models.JSONField(default=list)
    eligibility_criteria = models.JSONField(default=dict)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['provider', 'insurance_type']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.provider.name} - {self.name}"

    # ------------------------------------------------------------------
    # Pricing
    # ------------------------------------------------------------------

    def calculate_premium(
        self,
        coverage_amount: Decimal,
        tenure_months: int,
    ) -> Decimal:
        """
        Return the premium the customer must pay for a given coverage
        and tenure.

        Server-side calculation — clients cannot influence the amount.

        v1 formula:
            rate = premium_min / coverage_amount_min
            premium = coverage_amount * rate

        Bounded between premium_min and premium_max.
        """
        coverage_amount = Decimal(str(coverage_amount)).quantize(
            MONEY_QUANTUM
        )

        if coverage_amount <= Decimal("0.00"):
            raise ValueError("Coverage amount must be greater than zero.")

        coverage_min = Decimal(str(self.coverage_amount_min))
        premium_min = Decimal(str(self.premium_min))
        premium_max = Decimal(str(self.premium_max))

        if coverage_min <= Decimal("0.00"):
            return premium_min.quantize(MONEY_QUANTUM)

        rate = premium_min / coverage_min

        premium = (coverage_amount * rate).quantize(MONEY_QUANTUM)

        if premium < premium_min:
            premium = premium_min
        if premium > premium_max:
            premium = premium_max

        return premium.quantize(MONEY_QUANTUM)


class InsurancePolicy(models.Model):
    """User's insurance policies"""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
        ('CLAIMED', 'Claimed'),
        ('SUSPENDED', 'Suspended'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='insurance_policies',
    )
    product = models.ForeignKey(
        InsuranceProduct,
        on_delete=models.PROTECT,
        related_name='policies',
    )

    policy_number = models.CharField(max_length=50, unique=True)
    coverage_amount = models.DecimalField(max_digits=15, decimal_places=2)
    premium_amount = models.DecimalField(max_digits=10, decimal_places=2)
    tenure_months = models.IntegerField()

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    renewal_date = models.DateTimeField(null=True, blank=True)

    beneficiary_name = models.CharField(max_length=200, blank=True)
    beneficiary_relationship = models.CharField(max_length=50, blank=True)
    beneficiary_phone = models.CharField(max_length=20, blank=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='PENDING'
    )
    status_reason = models.TextField(blank=True)

    # Ledger journal that posted the premium payment.
    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='insurance_premiums',
        help_text="Ledger journal that posted the premium payment.",
    )

    documents = models.JSONField(default=list)
    additional_info = models.JSONField(default=dict)

    provider_reference = models.CharField(
        max_length=100, unique=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['policy_number']),
            models.Index(fields=['provider_reference']),
            models.Index(
                fields=['journal'],
                name='banking_policy_journal_idx',
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.policy_number} - {self.user.email}"

    # ------------------------------------------------------------------
    # Derived state
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        if self.status != 'ACTIVE':
            return False
        now = timezone.now()
        return self.start_date <= now <= self.end_date

    def is_expiring_soon(self, days: int = 30) -> bool:
        if self.status != 'ACTIVE':
            return False
        days_left = (self.end_date - timezone.now()).days
        return 0 < days_left <= days

    @property
    def days_until_expiry(self) -> int:
        if self.status != 'ACTIVE':
            return 0
        days_left = (self.end_date - timezone.now()).days
        return max(days_left, 0)

    # ------------------------------------------------------------------
    # Aggregates over claims
    #
    # These are NOT stored. Prior versions kept running counters on
    # the policy row, which could drift from the claim table on any
    # failed write, manual admin edit, or claim status transition.
    # ------------------------------------------------------------------

    @property
    def total_claimed(self) -> Decimal:
        from django.db.models import Sum

        total = (
            self.claims.aggregate(total=Sum("claim_amount"))["total"]
            or Decimal("0.00")
        )
        return Decimal(total).quantize(MONEY_QUANTUM)

    @property
    def total_paid(self) -> Decimal:
        from django.db.models import Sum

        total = (
            self.claims.aggregate(total=Sum("paid_amount"))["total"]
            or Decimal("0.00")
        )
        return Decimal(total).quantize(MONEY_QUANTUM)


class InsuranceClaim(models.Model):
    """Insurance claims filed by users"""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('REVIEWING', 'Reviewing'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PAID', 'Paid'),
        ('CLOSED', 'Closed'),
    ]

    policy = models.ForeignKey(
        InsurancePolicy,
        on_delete=models.CASCADE,
        related_name='claims',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='insurance_claims',
    )

    claim_number = models.CharField(max_length=50, unique=True)
    claim_amount = models.DecimalField(max_digits=15, decimal_places=2)
    approved_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    paid_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )

    incident_date = models.DateTimeField()
    incident_description = models.TextField()
    incident_location = models.CharField(max_length=255, blank=True)

    documents = models.JSONField(default=list)
    additional_info = models.JSONField(default=dict)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='PENDING'
    )
    status_reason = models.TextField(blank=True)
    reviewer_comments = models.TextField(blank=True)

    # Ledger journal that posted the payout.
    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='insurance_claim_payouts',
        help_text="Ledger journal that posted the claim payout.",
    )

    filed_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    provider_reference = models.CharField(
        max_length=100, unique=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['policy', 'status']),
            models.Index(fields=['user', 'filed_at']),
            models.Index(fields=['claim_number']),
            models.Index(
                fields=['journal'],
                name='banking_claim_journal_idx',
            ),
        ]
        ordering = ['-filed_at']

    def __str__(self):
        return f"Claim {self.claim_number} - {self.policy.policy_number}"