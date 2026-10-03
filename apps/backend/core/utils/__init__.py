"""
Shared utility helpers for Univa.

This package intentionally avoids eager imports of Django models.

Utilities that depend on Django models should import those models lazily
inside the functions that use them. This keeps lightweight utilities such
as serializers importable without requiring Django application
initialization.
"""

from __future__ import annotations

import socket
from collections.abc import Iterable
from typing import TYPE_CHECKING, Optional, Union
from urllib.parse import urljoin, urlparse

from celery.utils.log import get_task_logger
from django.conf import settings
from django.db.models import Model
from django.utils.encoding import iri_to_uri
from django.utils.text import slugify
from text_unidecode import unidecode


if TYPE_CHECKING:
    from django.contrib.sites.models import Site
    from django.utils.safestring import SafeText


task_logger = get_task_logger(__name__)


def get_domain(site: Optional["Site"] = None) -> str:
    """
    Return the configured public domain.

    If PUBLIC_URL is configured, its network location is returned.

    Otherwise, Django's current Site is resolved lazily.
    """
    if settings.PUBLIC_URL:
        return urlparse(settings.PUBLIC_URL).netloc

    if site is None:
        from django.contrib.sites.models import Site

        site = Site.objects.get_current()

    return site.domain


def get_public_url(domain: Optional[str] = None) -> str:
    """
    Return the public URL used by Univa.

    If PUBLIC_URL is configured, it is returned directly.

    Otherwise, the current Django Site is resolved lazily.
    """
    if settings.PUBLIC_URL:
        return settings.PUBLIC_URL

    if domain:
        host = domain
    else:
        from django.contrib.sites.models import Site

        host = Site.objects.get_current().domain

    protocol = "https" if settings.ENABLE_SSL else "http"

    return f"{protocol}://{host}"


def is_ssl_enabled() -> bool:
    """
    Return whether SSL/HTTPS is enabled.
    """
    if settings.PUBLIC_URL:
        return urlparse(settings.PUBLIC_URL).scheme.lower() == "https"

    return settings.ENABLE_SSL


def build_absolute_uri(
    location: str,
    domain: Optional[str] = None,
) -> str:
    """
    Create an absolute URI from a relative or absolute location.

    If ``location`` is already absolute, it remains unchanged.
    Otherwise it is resolved against the configured public URL.
    """
    current_uri = get_public_url(domain)

    location = urljoin(
        current_uri,
        location,
    )

    return iri_to_uri(location)


def get_client_ip(request):
    """
    Retrieve the client's IP address from a Django request.

    X-Forwarded-For is checked first. If no valid forwarded address
    exists, REMOTE_ADDR is used.
    """
    forwarded_for = request.META.get(
        "HTTP_X_FORWARDED_FOR",
        "",
    )

    ips = forwarded_for.split(",")

    for ip in ips:
        ip = ip.strip()

        if is_valid_ipv4(ip) or is_valid_ipv6(ip):
            return ip

    return request.META.get(
        "REMOTE_ADDR",
        None,
    )


def is_valid_ipv4(ip: str) -> bool:
    """
    Return True when ``ip`` is a valid IPv4 address.
    """
    try:
        socket.inet_pton(
            socket.AF_INET,
            ip,
        )
    except OSError:
        return False

    return True


def is_valid_ipv6(ip: str) -> bool:
    """
    Return True when ``ip`` is a valid IPv6 address.
    """
    try:
        socket.inet_pton(
            socket.AF_INET6,
            ip,
        )
    except OSError:
        return False

    return True


def generate_unique_slug(
    instance: Model,
    slugable_value: str,
    slug_field_name: str = "slug",
    *,
    additional_search_lookup=None,
) -> str:
    """
    Create a unique slug for a Django model instance.

    The generated slug is based on ``slugable_value``. If the slug
    already exists, a numeric suffix is appended and incremented until
    a unique value is found.

    ``additional_search_lookup`` can be supplied when uniqueness is
    scoped by additional model conditions.
    """
    slug = slugify(
        unidecode(slugable_value)
    )

    # If slugable_value contains only characters that cannot be used
    # in a slug, provide a deterministic fallback.
    if slug == "":
        slug = "-"

    ModelClass = instance.__class__

    search_field = f"{slug_field_name}__iregex"

    pattern = (
        rf"{slug}-\d+$|{slug}$"
    )

    lookup = {
        search_field: pattern,
    }

    if additional_search_lookup:
        lookup.update(
            additional_search_lookup
        )

    slug_values = (
        ModelClass._default_manager
        .filter(**lookup)
        .exclude(pk=instance.pk)
        .values_list(
            slug_field_name,
            flat=True,
        )
    )

    return prepare_unique_slug(
        slug,
        slug_values,
    )


def prepare_unique_slug(
    slug: str,
    slug_values: Iterable,
):
    """
    Prepare a unique slug from an iterable of existing slug values.
    """
    unique_slug: Union["SafeText", str] = slug

    extension = 1

    while unique_slug in slug_values:
        extension += 1
        unique_slug = f"{slug}-{extension}"

    return unique_slug


def prepare_unique_attribute_value_slug(
    attribute: "Attribute",
    slug: str,
):
    """
    Prepare a unique slug for an Attribute value.
    """
    value_slugs = (
        attribute.values
        .filter(slug__startswith=slug)
        .values_list(
            "slug",
            flat=True,
        )
    )

    return prepare_unique_slug(
        slug,
        value_slugs,
    )

