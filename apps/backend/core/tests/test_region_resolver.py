# core/tests/test_region_resolver.py

from django.test import TestCase

from core.models.region import Region, RegionLevel
from core.services.region_resolver import (
    resolve_from_geocode,
    _find_region,
    _unique_slug,
)


class TestResolveFromGeocode(TestCase):
    def test_empty_input_returns_none(self):
        self.assertIsNone(resolve_from_geocode({}))
        self.assertIsNone(resolve_from_geocode(None))

    def test_unknown_country_no_create_returns_none(self):
        result = resolve_from_geocode(
            {"country": "Atlantis", "country_code": "XX"},
            create_missing=False,
        )
        self.assertIsNone(result)

    def test_creates_country_when_allowed(self):
        result = resolve_from_geocode(
            {"country": "Testland", "country_code": "TL"},
            create_missing=True,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.region_type, RegionLevel.COUNTRY)
        self.assertEqual(result.slug, "testland")

    def test_creates_hierarchy(self):
        result = resolve_from_geocode(
            {
                "country": "Testland",
                "country_code": "TL",
                "state": "Teststate",
                "city": "Testcity",
            },
            create_missing=True,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.region_type, RegionLevel.CITY)
        self.assertEqual(result.parent.region_type, RegionLevel.STATE)
        self.assertEqual(
            result.parent.parent.region_type,
            RegionLevel.COUNTRY,
        )

    def test_stops_at_existing_level_when_not_creating(self):
        country = Region.objects.create(
            name="Nigeria",
            slug="nigeria",
            region_type=RegionLevel.COUNTRY,
            code="NG",
        )
        result = resolve_from_geocode(
            {
                "country": "Nigeria",
                "country_code": "NG",
                "state": "Lagos",
                "city": "Ikeja",
            },
            create_missing=False,
        )
        self.assertEqual(result, country)

    def test_reuses_existing_regions(self):
        country = Region.objects.create(
            name="Testland",
            slug="testland",
            region_type=RegionLevel.COUNTRY,
            code="TL",
        )
        result = resolve_from_geocode(
            {"country": "Testland", "country_code": "TL"},
            create_missing=True,
        )
        self.assertEqual(result.pk, country.pk)
        self.assertEqual(
            Region.objects.filter(slug="testland").count(),
            1,
        )


class TestHelpers(TestCase):
    def test_unique_slug_appends_counter(self):
        Region.objects.create(
            name="Test",
            slug="test",
            region_type=RegionLevel.COUNTRY,
        )
        slug = _unique_slug("test")
        self.assertEqual(slug, "test-2")

    def test_unique_slug_handles_empty(self):
        slug = _unique_slug("")
        self.assertEqual(slug, "region")

    def test_find_region_by_code(self):
        Region.objects.create(
            name="Nigeria",
            slug="nigeria",
            region_type=RegionLevel.COUNTRY,
            code="NG",
        )
        hit = _find_region(
            name="Anything",
            region_type=RegionLevel.COUNTRY,
            parent=None,
            code="NG",
        )
        self.assertIsNotNone(hit)
        self.assertEqual(hit.code, "NG")

    def test_find_region_by_slug(self):
        Region.objects.create(
            name="Nigeria",
            slug="nigeria",
            region_type=RegionLevel.COUNTRY,
        )
        hit = _find_region(
            name="Nigeria",
            region_type=RegionLevel.COUNTRY,
            parent=None,
        )
        self.assertIsNotNone(hit)

    def test_find_region_returns_none_for_empty(self):
        self.assertIsNone(
            _find_region(
                name="",
                region_type=RegionLevel.COUNTRY,
                parent=None,
            )
        )