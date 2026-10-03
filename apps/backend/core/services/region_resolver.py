# core/services/region_resolver.py

"""
Resolve coordinates to a Region.

Wraps `core.services.geocoding.reverse_geocode()` and maps its
string output (country/state/city) onto Region rows.

Design:

    - Region rows are normally pre-seeded by admins.
    - `resolve_region(lat, lng, create_missing=False)` returns the
      deepest matching Region or None.
    - If `settings.REGION_AUTO_CREATE` is True, missing levels are
      created lazily. This is intended for dev/staging only.

Usage:

    from core.services.region_resolver import resolve_region
    region = resolve_region(6.5244, 3.3792)   # Lagos, Nigeria
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.utils.text import slugify

from core.models.region import Region, RegionLevel
from core.services.geocoding import reverse_geocode

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------


def resolve_region(
    latitude: float,
    longitude: float,
    *,
    create_missing: bool | None = None,
) -> Region | None:
    """Resolve coordinates to the deepest matching Region."""
    geo = reverse_geocode(latitude, longitude)
    if not geo:
        return None

    if create_missing is None:
        create_missing = getattr(settings, "REGION_AUTO_CREATE", False)

    return resolve_from_geocode(geo, create_missing=create_missing)


def resolve_from_geocode(
    geo: dict,
    *,
    create_missing: bool = False,
) -> Region | None:
    """
    Resolve a reverse-geocode result dict to a Region.

    Dict shape (from core.services.geocoding.reverse_geocode):

        {
            "country":      "Nigeria",
            "country_code": "ng",
            "state":        "Lagos",
            "city":         "Ikeja",
            ...
        }
    """
    if not geo:
        return None

    country_name = (geo.get("country") or "").strip()
    country_code = (geo.get("country_code") or "").strip().upper()
    state_name = (geo.get("state") or "").strip()
    city_name = (geo.get("city") or "").strip()

    parent: Region | None = None

    # --- Country -----------------------------------------------------
    country = _find_region(
        name=country_name,
        region_type=RegionLevel.COUNTRY,
        parent=None,
        code=country_code,
    )
    if country is None:
        if not create_missing or not country_name:
            return None
        country = _create_region(
            name=country_name,
            region_type=RegionLevel.COUNTRY,
            parent=None,
            code=country_code,
        )
    parent = country

    # --- State -------------------------------------------------------
    if state_name:
        state = _find_region(
            name=state_name,
            region_type=RegionLevel.STATE,
            parent=parent,
        )
        if state is None:
            if not create_missing:
                return parent
            state = _create_region(
                name=state_name,
                region_type=RegionLevel.STATE,
                parent=parent,
            )
        parent = state

    # --- City --------------------------------------------------------
    if city_name:
        city = _find_region(
            name=city_name,
            region_type=RegionLevel.CITY,
            parent=parent,
        )
        if city is None:
            if not create_missing:
                return parent
            city = _create_region(
                name=city_name,
                region_type=RegionLevel.CITY,
                parent=parent,
            )
        parent = city

    # Neighborhood and Market are not returned by Nominatim. Stop at City.
    return parent


# ---------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------


def _find_region(
    *,
    name: str,
    region_type: str,
    parent: Region | None,
    code: str = "",
) -> Region | None:
    """
    Look up a Region by (name, region_type, parent). Falls back to slug.
    """
    if not name and not code:
        return None

    qs = Region.objects.filter(region_type=region_type, parent=parent)

    if code:
        hit = qs.filter(code__iexact=code).first()
        if hit:
            return hit

    slug = slugify(name, allow_unicode=True)
    if slug:
        hit = qs.filter(slug=slug).first()
        if hit:
            return hit

    if name:
        return qs.filter(name__iexact=name).first()

    return None


@transaction.atomic
def _create_region(
    *,
    name: str,
    region_type: str,
    parent: Region | None,
    code: str = "",
) -> Region:
    """Create a Region if none matches."""
    existing = _find_region(
        name=name,
        region_type=region_type,
        parent=parent,
        code=code,
    )
    if existing:
        return existing

    slug = _unique_slug(slugify(name, allow_unicode=True))
    region = Region.objects.create(
        name=name,
        slug=slug,
        region_type=region_type,
        parent=parent,
        code=code,
    )
    logger.info(
        "Region auto-created: %s (%s, parent=%s)",
        region.name,
        region.region_type,
        parent.slug if parent else None,
    )
    return region


def _unique_slug(base: str) -> str:
    """Return a globally unique slug based on `base`."""
    if not base:
        base = "region"

    slug = base
    i = 2
    while Region.objects.filter(slug=slug).exists():
        slug = f"{base}-{i}"
        i += 1
    return slug