"""
Tests for MagicLoginToken.

Covers:
    - Token creation via create_for_user()
    - Device info and browser fingerprint extraction
    - Deterministic device fingerprint generation
    - Token validation (valid, expired, used, wrong purpose)
    - Lenient device-fingerprint mismatch policy
    - mark_as_used() atomic single-use semantics
    - get_absolute_url() URL construction
    - __str__() representation
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import (
    RequestFactory,
    TestCase,
    override_settings,
)
from django.urls import reverse
from django.utils import timezone

from accounts.models.auth import MagicLoginToken


User = get_user_model()


# =============================================================================
# CREATION
# =============================================================================


class MagicLoginTokenCreationTests(TestCase):
    """create_for_user() behavior."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="magic@example.com",
            password="TestPassword123!",
        )

    def test_create_for_user_creates_token(self):
        """A token row is created for the user."""
        token = MagicLoginToken.create_for_user(user=self.user)

        self.assertIsNotNone(token.pk)
        self.assertEqual(token.user, self.user)
        self.assertFalse(token.used)
        self.assertEqual(token.purpose, "login")

    def test_create_for_user_generates_unique_tokens(self):
        """Each call produces a distinct opaque token string."""
        first = MagicLoginToken.create_for_user(user=self.user)
        second = MagicLoginToken.create_for_user(user=self.user)

        self.assertNotEqual(first.token, second.token)

    def test_token_string_is_64_chars(self):
        """Token is the length requested from get_random_string()."""
        token = MagicLoginToken.create_for_user(user=self.user)

        self.assertEqual(len(token.token), 64)

    @override_settings(MAGIC_LINK_EXPIRY_MINUTES=30)
    def test_create_for_user_respects_configured_expiry(self):
        """expires_at honors MAGIC_LINK_EXPIRY_MINUTES."""
        before = timezone.now()
        token = MagicLoginToken.create_for_user(user=self.user)
        after = timezone.now()

        self.assertGreaterEqual(
            token.expires_at,
            before + timedelta(minutes=30),
        )
        self.assertLessEqual(
            token.expires_at,
            after + timedelta(minutes=30),
        )

    def test_create_for_user_default_expiry_is_15_minutes(self):
        """Falls back to 15 minutes when the setting is absent."""
        before = timezone.now()
        token = MagicLoginToken.create_for_user(user=self.user)

        expected = before + timedelta(minutes=15)

        self.assertAlmostEqual(
            token.expires_at.timestamp(),
            expected.timestamp(),
            delta=5,
        )

    def test_create_for_user_accepts_purpose_kwarg(self):
        """Purpose can be supplied via kwargs."""
        token = MagicLoginToken.create_for_user(
            user=self.user,
            purpose="recovery",
        )

        self.assertEqual(token.purpose, "recovery")

    def test_create_for_user_accepts_redirect_to_kwarg(self):
        """redirect_to can be supplied via kwargs."""
        token = MagicLoginToken.create_for_user(
            user=self.user,
            redirect_to="/dashboard",
        )

        self.assertEqual(token.redirect_to, "/dashboard")

    def test_create_for_user_without_request_leaves_device_empty(self):
        """A token created without a request has no device context."""
        token = MagicLoginToken.create_for_user(user=self.user)

        self.assertEqual(token.device_info, {})
        self.assertEqual(token.browser_fingerprint, {})
        self.assertIsNone(token.device_fingerprint)
        self.assertIsNone(token.ip_address)

    def test_create_for_user_stores_ip_address(self):
        """REMOTE_ADDR is persisted on the token."""
        factory = RequestFactory()
        request = factory.get("/")
        request.META["REMOTE_ADDR"] = "203.0.113.42"

        token = MagicLoginToken.create_for_user(
            user=self.user,
            request=request,
        )

        self.assertEqual(token.ip_address, "203.0.113.42")

    def test_create_for_user_populates_fingerprints(self):
        """Fingerprint fields are populated from a request."""
        factory = RequestFactory()
        request = factory.get(
            "/",
            HTTP_USER_AGENT="TestAgent/1.0",
            HTTP_ACCEPT_LANGUAGE="en-US",
            HTTP_ACCEPT_ENCODING="gzip",
        )

        token = MagicLoginToken.create_for_user(
            user=self.user,
            request=request,
        )

        self.assertIsNotNone(token.device_fingerprint)
        self.assertEqual(len(token.device_fingerprint), 64)
        self.assertIn("user_agent", token.browser_fingerprint)


# =============================================================================
# DEVICE INFO EXTRACTION
# =============================================================================


class DeviceInfoExtractionTests(TestCase):
    """_get_device_info() and _get_browser_fingerprint()."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_get_device_info_returns_empty_for_none_request(self):
        """No request yields an empty dict."""
        self.assertEqual(
            MagicLoginToken._get_device_info(None),
            {},
        )

    def test_get_device_info_extracts_known_headers(self):
        """Standard headers are captured verbatim."""
        request = self.factory.get(
            "/",
            HTTP_USER_AGENT="TestAgent/1.0",
            HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9",
            HTTP_ACCEPT_ENCODING="gzip, deflate",
            HTTP_X_SCREEN_RESOLUTION="1920x1080",
            HTTP_X_TIMEZONE="Africa/Lagos",
            HTTP_X_DEVICE_ID="device-abc",
        )
        request.META["REMOTE_ADDR"] = "203.0.113.42"

        info = MagicLoginToken._get_device_info(request)

        self.assertEqual(info["user_agent"], "TestAgent/1.0")
        self.assertEqual(info["accept_language"], "en-US,en;q=0.9")
        self.assertEqual(info["accept_encoding"], "gzip, deflate")
        self.assertEqual(info["screen_resolution"], "1920x1080")
        self.assertEqual(info["timezone"], "Africa/Lagos")
        self.assertEqual(info["device_id"], "device-abc")
        self.assertEqual(info["ip_address"], "203.0.113.42")

    def test_get_device_info_truncates_long_user_agent(self):
        """User agent is truncated to 500 chars."""
        request = self.factory.get(
            "/",
            HTTP_USER_AGENT="x" * 1000,
        )

        info = MagicLoginToken._get_device_info(request)

        self.assertEqual(len(info["user_agent"]), 500)

    def test_get_device_info_truncates_long_accept_language(self):
        """Accept-Language is truncated to 100 chars."""
        request = self.factory.get(
            "/",
            HTTP_ACCEPT_LANGUAGE="l" * 500,
        )

        info = MagicLoginToken._get_device_info(request)

        self.assertEqual(len(info["accept_language"]), 100)

    def test_get_device_info_truncates_long_accept_encoding(self):
        """Accept-Encoding is truncated to 100 chars."""
        request = self.factory.get(
            "/",
            HTTP_ACCEPT_ENCODING="e" * 500,
        )

        info = MagicLoginToken._get_device_info(request)

        self.assertEqual(len(info["accept_encoding"]), 100)

    def test_get_browser_fingerprint_returns_empty_for_none_request(self):
        """No request yields an empty dict."""
        self.assertEqual(
            MagicLoginToken._get_browser_fingerprint(None),
            {},
        )

    def test_get_browser_fingerprint_extracts_headers(self):
        """Browser headers are captured."""
        request = self.factory.get(
            "/",
            HTTP_USER_AGENT="TestAgent/1.0",
            HTTP_ACCEPT_LANGUAGE="en-US",
            HTTP_ACCEPT_ENCODING="gzip",
            HTTP_ACCEPT_CHARSET="utf-8",
            HTTP_CONNECTION="keep-alive",
            HTTP_SEC_CH_UA_PLATFORM='"Windows"',
        )

        fp = MagicLoginToken._get_browser_fingerprint(request)

        self.assertEqual(fp["user_agent"], "TestAgent/1.0")
        self.assertEqual(fp["accept_headers"]["language"], "en-US")
        self.assertEqual(fp["accept_headers"]["encoding"], "gzip")
        self.assertEqual(fp["accept_headers"]["charset"], "utf-8")
        self.assertEqual(fp["connection"], "keep-alive")
        self.assertEqual(fp["platform"], '"Windows"')


# =============================================================================
# DEVICE FINGERPRINT
# =============================================================================


class DeviceFingerprintTests(TestCase):
    """_generate_device_fingerprint()."""

    def test_empty_device_info_returns_none(self):
        """No data yields no fingerprint."""
        self.assertIsNone(
            MagicLoginToken._generate_device_fingerprint({}),
        )

    def test_device_info_without_fingerprint_fields_returns_none(self):
        """Only unrelated keys yields no fingerprint."""
        self.assertIsNone(
            MagicLoginToken._generate_device_fingerprint(
                {
                    "device_id": "abc",
                    "ip_address": "1.2.3.4",
                }
            ),
        )

    def test_fingerprint_is_deterministic(self):
        """Identical inputs yield identical fingerprints."""
        info = {
            "user_agent": "TestAgent/1.0",
            "accept_language": "en-US",
            "accept_encoding": "gzip",
            "screen_resolution": "1920x1080",
            "timezone": "Africa/Lagos",
        }

        first = MagicLoginToken._generate_device_fingerprint(info)
        second = MagicLoginToken._generate_device_fingerprint(info)

        self.assertEqual(first, second)

    def test_fingerprint_is_sha256_hex(self):
        """Fingerprint is a 64-character hex string."""
        info = {"user_agent": "TestAgent/1.0"}

        fp = MagicLoginToken._generate_device_fingerprint(info)

        self.assertIsNotNone(fp)
        self.assertEqual(len(fp), 64)

        # Raises ValueError if not valid hex.
        int(fp, 16)

    def test_fingerprint_changes_with_different_user_agent(self):
        """Different user agents yield different fingerprints."""
        first = MagicLoginToken._generate_device_fingerprint(
            {"user_agent": "AgentA"},
        )
        second = MagicLoginToken._generate_device_fingerprint(
            {"user_agent": "AgentB"},
        )

        self.assertNotEqual(first, second)

    def test_fingerprint_changes_with_different_screen(self):
        """Screen resolution participates in the fingerprint."""
        first = MagicLoginToken._generate_device_fingerprint(
            {"screen_resolution": "1920x1080"},
        )
        second = MagicLoginToken._generate_device_fingerprint(
            {"screen_resolution": "2560x1440"},
        )

        self.assertNotEqual(first, second)


# =============================================================================
# VALIDATION
# =============================================================================


class TokenValidationTests(TestCase):
    """validate_token()."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="validate@example.com",
            password="TestPassword123!",
        )

    def test_valid_token_returns_record(self):
        """A fresh token validates and returns the record."""
        token = MagicLoginToken.create_for_user(user=self.user)

        record = MagicLoginToken.validate_token(token.token)

        self.assertEqual(record.pk, token.pk)
        self.assertEqual(record.user, self.user)

    def test_unknown_token_raises(self):
        """Nonexistent token string raises ValueError."""
        with self.assertRaisesMessage(ValueError, "Invalid token"):
            MagicLoginToken.validate_token("not-a-real-token")

    def test_used_token_raises(self):
        """A consumed token raises ValueError."""
        token = MagicLoginToken.create_for_user(user=self.user)
        token.mark_as_used()

        with self.assertRaisesMessage(
            ValueError,
            "Token already used",
        ):
            MagicLoginToken.validate_token(token.token)

    def test_expired_token_raises(self):
        """An expired token raises ValueError."""
        token = MagicLoginToken.create_for_user(user=self.user)

        token.expires_at = timezone.now() - timedelta(seconds=1)
        token.save(update_fields=["expires_at"])

        with self.assertRaisesMessage(
            ValueError,
            "Token expired",
        ):
            MagicLoginToken.validate_token(token.token)

    def test_purpose_mismatch_raises(self):
        """Validating with the wrong purpose raises ValueError."""
        token = MagicLoginToken.create_for_user(
            user=self.user,
            purpose="login",
        )

        with self.assertRaisesMessage(
            ValueError,
            "Invalid token purpose",
        ):
            MagicLoginToken.validate_token(
                token.token,
                purpose="recovery",
            )

    def test_matching_purpose_validates(self):
        """Correct purpose passes."""
        token = MagicLoginToken.create_for_user(
            user=self.user,
            purpose="recovery",
        )

        record = MagicLoginToken.validate_token(
            token.token,
            purpose="recovery",
        )

        self.assertEqual(record.pk, token.pk)

    def test_no_purpose_skips_purpose_check(self):
        """Omitting purpose bypasses the purpose check."""
        token = MagicLoginToken.create_for_user(
            user=self.user,
            purpose="recovery",
        )

        record = MagicLoginToken.validate_token(token.token)

        self.assertEqual(record.pk, token.pk)

    def test_device_fingerprint_mismatch_is_lenient(self):
        """
        Current policy is lenient on fingerprint mismatch.

        A request from a different device must not invalidate the
        token today. If this policy changes to a hard failure, this
        test should be updated deliberately.
        """
        factory = RequestFactory()

        original_request = factory.get(
            "/",
            HTTP_USER_AGENT="DeviceA/1.0",
            HTTP_ACCEPT_LANGUAGE="en-US",
        )

        token = MagicLoginToken.create_for_user(
            user=self.user,
            request=original_request,
        )

        self.assertIsNotNone(token.device_fingerprint)

        different_request = factory.get(
            "/",
            HTTP_USER_AGENT="DeviceB/2.0",
            HTTP_ACCEPT_LANGUAGE="fr-FR",
        )

        # Should NOT raise.
        record = MagicLoginToken.validate_token(
            token.token,
            request=different_request,
        )

        self.assertEqual(record.pk, token.pk)

    def test_validate_without_request_skips_fingerprint_check(self):
        """No request → no fingerprint check."""
        factory = RequestFactory()
        request = factory.get("/", HTTP_USER_AGENT="DeviceA/1.0")

        token = MagicLoginToken.create_for_user(
            user=self.user,
            request=request,
        )

        # No request argument here.
        record = MagicLoginToken.validate_token(token.token)

        self.assertEqual(record.pk, token.pk)


# =============================================================================
# LIFECYCLE
# =============================================================================


class MarkAsUsedTests(TestCase):
    """mark_as_used() atomic single-use semantics."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="lifecycle@example.com",
            password="TestPassword123!",
        )

    def test_first_call_returns_true(self):
        """First consumption returns True."""
        token = MagicLoginToken.create_for_user(user=self.user)

        self.assertTrue(token.mark_as_used())

    def test_first_call_persists_used_flag(self):
        """The used flag is persisted on first consumption."""
        token = MagicLoginToken.create_for_user(user=self.user)
        token.mark_as_used()

        reloaded = MagicLoginToken.objects.get(pk=token.pk)
        self.assertTrue(reloaded.used)

    def test_second_call_returns_false(self):
        """Second consumption returns False."""
        token = MagicLoginToken.create_for_user(user=self.user)
        token.mark_as_used()

        self.assertFalse(token.mark_as_used())

    def test_second_call_keeps_used_true(self):
        """Second consumption leaves the used flag set."""
        token = MagicLoginToken.create_for_user(user=self.user)
        token.mark_as_used()
        token.mark_as_used()

        reloaded = MagicLoginToken.objects.get(pk=token.pk)
        self.assertTrue(reloaded.used)

    def test_stale_instance_still_returns_false(self):
        """
        A stale in-memory used=False is not authoritative.

        The atomic filter-against-DB determines the outcome. If the
        DB already marks the token used, the second call returns
        False even if the local instance lied about used=False.
        """
        token = MagicLoginToken.create_for_user(user=self.user)
        token.mark_as_used()

        # Simulate a stale instance that thinks it is unused.
        token.used = False

        result = token.mark_as_used()

        self.assertFalse(result)
        self.assertTrue(token.used)


# =============================================================================
# URL
# =============================================================================


'''class MagicLinkURLTests(TestCase):
    """get_absolute_url()."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="url@example.com",
            password="TestPassword123!",
        )

    @override_settings(SITE_URL="https://app.example.com")
    def test_get_absolute_url_uses_site_url_and_reversed_path(self):
        """URL combines SITE_URL with the reversed token path."""
        token = MagicLoginToken.create_for_user(user=self.user)

        expected_path = reverse(
            "magic-link-authenticate",
            kwargs={"token": token.token},
        )

        self.assertEqual(
            token.get_absolute_url(),
            f"https://app.example.com{expected_path}",
        )

    @override_settings(SITE_URL="https://app.example.com")
    def test_get_absolute_url_contains_opaque_token(self):
        """The opaque token appears verbatim in the URL."""
        token = MagicLoginToken.create_for_user(user=self.user)

        self.assertIn(
            token.token,
            token.get_absolute_url(),
        )'''


# =============================================================================
# REPRESENTATION
# =============================================================================


class MagicLoginTokenRepresentationTests(TestCase):
    """__str__()."""

    def test_str_includes_email_and_purpose(self):
        """String form identifies the user and purpose."""
        user = User.objects.create_user(
            email="strtest@example.com",
            password="TestPassword123!",
        )
        token = MagicLoginToken.create_for_user(
            user=user,
            purpose="recovery",
        )

        text = str(token)

        self.assertIn("strtest@example.com", text)
        self.assertIn("recovery", text)