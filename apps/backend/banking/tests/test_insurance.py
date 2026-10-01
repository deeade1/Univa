"""
Unit tests for apps/backend/banking/models/insurance.py

Covers:
    - InsuranceProvider
    - InsuranceProduct
    - InsurancePolicy (including is_active / is_expiring_soon helpers)
    - InsuranceClaim

Notes:
    - Uses the project's central User model via ``settings.AUTH_USER_MODEL``.
    - ``Account`` is not required for insurance models, so tests stay
      self-contained.
    - Date-based helpers are tested with both real timezone.now() values
      and backdated entries to exercise expiry/active edges.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from django.utils.text import slugify

from banking.models.insurance import (
    InsuranceClaim,
    InsurancePolicy,
    InsuranceProduct,
    InsuranceProvider,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(**kwargs):
    defaults = {
        "email": "insured@example.com",
        "password": "testpass123",
        "first_name": "Jane",
        "last_name": "Insured",
        "phone_number": "+2348000000001",
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def make_provider(**kwargs):
    defaults = {
        "name": "Acme Insurance",
        "code": "ACME",
        "website": "https://acme.example.com",
        "phone": "+2348000000002",
        "email": "hello@acme.example.com",
    }
    defaults.update(kwargs)
    return InsuranceProvider.objects.create(**defaults)


def make_product(provider=None, **kwargs):
    provider = provider or make_provider()
    defaults = {
        "provider": provider,
        "name": "Motor Comprehensive",
        "slug": "motor-comprehensive",
        "insurance_type": "MOTOR",
        "description": "Full motor cover",
        "coverage_details": {"theft": True, "accident": True},
        "exclusions": ["racing", "DUI"],
        "coverage_amount_min": Decimal("100000.00"),
        "coverage_amount_max": Decimal("10000000.00"),
        "premium_min": Decimal("5000.00"),
        "premium_max": Decimal("250000.00"),
        "payment_frequency": "ANNUALLY",
        "min_tenure_months": 6,
        "max_tenure_months": 36,
        "default_tenure_months": 12,
        "required_documents": ["vehicle_registration", "drivers_license"],
        "eligibility_criteria": {"min_age": 18, "max_age": 70},
    }
    defaults.update(kwargs)
    return InsuranceProduct.objects.create(**defaults)


def make_policy(user=None, product=None, **kwargs):
    user = user or make_user()
    product = product or make_product()
    now = timezone.now()
    defaults = {
        "user": user,
        "product": product,
        "policy_number": "POL-0001",
        "coverage_amount": Decimal("1000000.00"),
        "premium_amount": Decimal("25000.00"),
        "tenure_months": 12,
        "start_date": now - timedelta(days=10),
        "end_date": now + timedelta(days=355),
        "status": "ACTIVE",
        "provider_reference": "ACME-REF-0001",
    }
    defaults.update(kwargs)
    return InsurancePolicy.objects.create(**defaults)


def make_claim(policy=None, user=None, **kwargs):
    policy = policy or make_policy()
    user = user or policy.user

    defaults = {
        "policy": policy,
        "user": user,
        "claim_number": "CLM-0001",
        "claim_amount": Decimal("150000.00"),
        "incident_date": timezone.now() - timedelta(days=3),
        "incident_description": "Minor collision at roundabout",
        "incident_location": "Lagos",
        "provider_reference": "ACME-CLM-0001",
    }

    defaults.update(kwargs)

    return InsuranceClaim.objects.create(**defaults)


# ---------------------------------------------------------------------------
# InsuranceProvider
# ---------------------------------------------------------------------------

class InsuranceProviderTests(TestCase):
    def test_create_provider(self):
        provider = make_provider()
        self.assertEqual(provider.code, "ACME")
        self.assertTrue(provider.is_active)
        self.assertEqual(str(provider), "Acme Insurance")

    def test_code_is_unique(self):
        make_provider(code="UNIQUE")
        with self.assertRaises(IntegrityError):
            make_provider(code="UNIQUE", name="Other")

    def test_optional_fields_blank(self):
        provider = InsuranceProvider.objects.create(name="Minimal", code="MIN")
        self.assertEqual(provider.website, "")
        self.assertEqual(provider.phone, "")
        self.assertEqual(provider.email, "")

    def test_created_and_updated_timestamps(self):
        provider = make_provider()
        self.assertIsNotNone(provider.created_at)
        self.assertIsNotNone(provider.updated_at)


# ---------------------------------------------------------------------------
# InsuranceProduct
# ---------------------------------------------------------------------------

class InsuranceProductTests(TestCase):
    def setUp(self):
        self.provider = make_provider()

    def test_create_product(self):
        product = make_product(provider=self.provider)
        self.assertEqual(product.insurance_type, "MOTOR")
        self.assertEqual(product.payment_frequency, "ANNUALLY")
        self.assertEqual(str(product), "Acme Insurance - Motor Comprehensive")

    def test_slug_is_unique(self):
        make_product(provider=self.provider, slug="unique-slug")
        with self.assertRaises(IntegrityError):
            make_product(
                provider=self.provider,
                slug="unique-slug",
                name="Another",
                insurance_type="HEALTH",
            )

    def test_defaults_for_json_fields(self):
        product = InsuranceProduct.objects.create(
            provider=self.provider,
            name="Device Cover",
            slug="device-cover",
            insurance_type="DEVICE",
            description="Phone protection",
            coverage_amount_min=Decimal("10000.00"),
            coverage_amount_max=Decimal("500000.00"),
            premium_min=Decimal("1000.00"),
            premium_max=Decimal("20000.00"),
            payment_frequency="MONTHLY",
            min_tenure_months=1,
            max_tenure_months=24,
            default_tenure_months=12,
        )
        self.assertEqual(product.coverage_details, {})
        self.assertEqual(product.exclusions, [])
        self.assertEqual(product.required_documents, [])
        self.assertEqual(product.eligibility_criteria, {})
        self.assertEqual(product.metadata, {})

    def test_ordering_by_created_desc(self):
        p1 = make_product(
            provider=self.provider,
            slug="first",
        )
        p2 = make_product(
            provider=self.provider,
            slug="second",
            insurance_type="HEALTH",
        )

        self.assertEqual(
            list(InsuranceProduct.objects.all())[0],
            p2,
        )
        self.assertEqual(
            list(InsuranceProduct.objects.all())[1],
            p1,
        )

    def test_provider_protected_from_delete(self):
        make_product(provider=self.provider)
        with self.assertRaises(Exception):
            self.provider.delete()


# ---------------------------------------------------------------------------
# InsurancePolicy
# ---------------------------------------------------------------------------

class InsurancePolicyTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product()

    def test_create_policy(self):
        policy = make_policy(user=self.user, product=self.product)
        self.assertEqual(policy.status, "ACTIVE")
        self.assertIn(policy.policy_number, str(policy))
        self.assertIn(self.user.email, str(policy))

    def test_policy_number_unique(self):
        make_policy(user=self.user, product=self.product, policy_number="POL-DUP")
        with self.assertRaises(IntegrityError):
            make_policy(
                user=self.user, product=self.product, policy_number="POL-DUP"
            )

    def test_provider_reference_unique(self):
        make_policy(user=self.user, product=self.product, provider_reference="REF-X")
        with self.assertRaises(IntegrityError):
            make_policy(
                user=self.user,
                product=self.product,
                policy_number="POL-0002",
                provider_reference="REF-X",
            )

    def test_defaults(self):
        policy = InsurancePolicy.objects.create(
            user=self.user,
            product=self.product,
            policy_number="POL-DEFAULTS",
            coverage_amount=Decimal("1000000.00"),
            premium_amount=Decimal("25000.00"),
            tenure_months=12,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=365),
        )
        self.assertEqual(policy.status, "PENDING")
        self.assertEqual(policy.total_claimed, Decimal("0"))
        self.assertEqual(policy.total_paid, Decimal("0"))
        self.assertEqual(policy.documents, [])
        self.assertEqual(policy.additional_info, {})
        self.assertEqual(policy.metadata, {})

    def test_is_active_true_within_window(self):
        policy = make_policy(user=self.user, product=self.product)
        self.assertTrue(policy.is_active())

    def test_is_active_false_when_not_active_status(self):
        policy = make_policy(
            user=self.user, product=self.product, status="CANCELLED"
        )
        self.assertFalse(policy.is_active())

    def test_is_active_false_before_start(self):
        policy = make_policy(
            user=self.user,
            product=self.product,
            start_date=timezone.now() + timedelta(days=5),
            end_date=timezone.now() + timedelta(days=365),
        )
        self.assertFalse(policy.is_active())

    def test_is_active_false_after_end(self):
        policy = make_policy(
            user=self.user,
            product=self.product,
            start_date=timezone.now() - timedelta(days=400),
            end_date=timezone.now() - timedelta(days=10),
        )
        self.assertFalse(policy.is_active())

    def test_is_expiring_soon_true(self):
        policy = make_policy(
            user=self.user,
            product=self.product,
            start_date=timezone.now() - timedelta(days=350),
            end_date=timezone.now() + timedelta(days=15),
        )
        self.assertTrue(policy.is_expiring_soon(days=30))

    def test_is_expiring_soon_false_when_not_active(self):
        policy = make_policy(
            user=self.user,
            product=self.product,
            status="EXPIRED",
            end_date=timezone.now() + timedelta(days=15),
        )
        self.assertFalse(policy.is_expiring_soon())

    def test_is_expiring_soon_false_when_far_out(self):
        policy = make_policy(
            user=self.user,
            product=self.product,
            end_date=timezone.now() + timedelta(days=200),
        )
        self.assertFalse(policy.is_expiring_soon(days=30))

    def test_is_expiring_soon_false_when_already_expired(self):
        policy = make_policy(
            user=self.user,
            product=self.product,
            start_date=timezone.now() - timedelta(days=400),
            end_date=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(policy.is_expiring_soon(days=30))

    def test_ordering_by_created_desc(self):
        p1 = make_policy(
            user=self.user,
            product=self.product,
            policy_number="POL-A",
            provider_reference="ACME-REF-0001",
        )

        p2 = make_policy(
            user=self.user,
            product=self.product,
            policy_number="POL-B",
            provider_reference="ACME-REF-0002",
        )

        self.assertEqual(
            list(InsurancePolicy.objects.all())[0],
            p2,
        )
        self.assertEqual(
            list(InsurancePolicy.objects.all())[1],
            p1,
        )

    def test_user_protected_from_delete(self):
        make_policy(user=self.user, product=self.product)
        with self.assertRaises(Exception):
            self.user.delete()

    def test_product_protected_from_delete(self):
        make_policy(user=self.user, product=self.product)
        with self.assertRaises(Exception):
            self.product.delete()


# ---------------------------------------------------------------------------
# InsuranceClaim
# ---------------------------------------------------------------------------

class InsuranceClaimTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product()
        self.policy = make_policy(user=self.user, product=self.product)

    def test_create_claim(self):
        claim = make_claim(policy=self.policy, user=self.user)
        self.assertEqual(claim.status, "PENDING")
        self.assertEqual(claim.paid_amount, Decimal("0"))
        self.assertIn(claim.claim_number, str(claim))
        self.assertIn(self.policy.policy_number, str(claim))

    def test_claim_number_unique(self):
        make_claim(
            policy=self.policy, user=self.user, claim_number="CLM-DUP"
        )
        with self.assertRaises(IntegrityError):
            make_claim(
                policy=self.policy,
                user=self.user,
                claim_number="CLM-DUP",
                provider_reference="OTHER-REF",
            )

    def test_provider_reference_unique(self):
        make_claim(
            policy=self.policy,
            user=self.user,
            claim_number="CLM-A",
            provider_reference="REF-CLAIM",
        )
        with self.assertRaises(IntegrityError):
            make_claim(
                policy=self.policy,
                user=self.user,
                claim_number="CLM-B",
                provider_reference="REF-CLAIM",
            )

    def test_defaults(self):
        claim = InsuranceClaim.objects.create(
            policy=self.policy,
            user=self.user,
            claim_number="CLM-DEFAULTS",
            claim_amount=Decimal("5000.00"),
            incident_date=timezone.now(),
            incident_description="Test incident",
        )
        self.assertEqual(claim.status, "PENDING")
        self.assertEqual(claim.paid_amount, Decimal("0"))
        self.assertEqual(claim.documents, [])
        self.assertEqual(claim.additional_info, {})
        self.assertEqual(claim.metadata, {})
        self.assertIsNotNone(claim.filed_at)
        self.assertIsNone(claim.reviewed_at)
        self.assertIsNone(claim.approved_at)
        self.assertIsNone(claim.paid_at)
        self.assertIsNone(claim.approved_amount)

    def test_ordering_by_filed_at_desc(self):
        c1 = make_claim(
            policy=self.policy,
            user=self.user,
            claim_number="CLM-1",
            provider_reference="REF-1",
        )
        c2 = make_claim(
            policy=self.policy,
            user=self.user,
            claim_number="CLM-2",
            provider_reference="REF-2",
        )
        self.assertEqual(list(InsuranceClaim.objects.all())[0], c2)
        self.assertEqual(list(InsuranceClaim.objects.all())[1], c1)

    def test_policy_cascade_delete_removes_claims(self):
        claim = make_claim(
            policy=self.policy, user=self.user, provider_reference="REF-CASCADE"
        )
        claim_pk = claim.pk
        self.policy.delete()
        self.assertFalse(InsuranceClaim.objects.filter(pk=claim_pk).exists())

    def test_user_protected_from_delete(self):
        make_claim(
            policy=self.policy, user=self.user, provider_reference="REF-PROT"
        )
        with self.assertRaises(Exception):
            self.user.delete()

    def test_related_name_claims(self):
        make_claim(
            policy=self.policy, user=self.user, provider_reference="REF-REL"
        )
        self.assertEqual(self.policy.claims.count(), 1)

    def test_related_name_on_user_and_policy(self):
        make_claim(
            policy=self.policy, user=self.user, provider_reference="REF-REL2"
        )
        self.assertEqual(self.user.insurance_claims.count(), 1)
        self.assertEqual(self.user.insurance_policies.count(), 1)


# ---------------------------------------------------------------------------
# Cross-model / integration-ish tests
# ---------------------------------------------------------------------------

class InsuranceIntegrationTests(TestCase):
    def test_full_lifecycle(self):
        user = make_user(email="lifecycle@example.com")
        provider = make_provider(code="LIFE", name="LifeCo")
        product = make_product(
            provider=provider,
            slug="life-cover",
            name="Life Cover",
            insurance_type="LIFE",
        )
        policy = make_policy(
            user=user,
            product=product,
            policy_number="POL-LIFE-1",
            provider_reference="LIFE-REF-1",
        )
        claim = make_claim(
            policy=policy,
            user=user,
            claim_number="CLM-LIFE-1",
            provider_reference="LIFE-CLM-REF-1",
            status="APPROVED",
            approved_amount=Decimal("500000.00"),
            approved_at=timezone.now(),
        )

        self.assertEqual(policy.product.provider.code, "LIFE")
        self.assertEqual(claim.policy.policy_number, "POL-LIFE-1")
        self.assertEqual(claim.status, "APPROVED")
        self.assertEqual(claim.approved_amount, Decimal("500000.00"))
        self.assertTrue(policy.is_active())

    def test_provider_products_related_name(self):
        provider = make_provider(code="REL")
        make_product(provider=provider, slug="rel-a", name="A")
        make_product(provider=provider, slug="rel-b", name="B", insurance_type="HEALTH")
        self.assertEqual(provider.products.count(), 2)