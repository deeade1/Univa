# apps/backend/ecommerce/models/enums/_base.py

"""
Shared helpers for enum modules.

Enums in this package use plain classes with a CHOICES list, matching
Django's `choices=` convention. This is intentional:

    - Django's `TextChoices` requires Django-specific imports, which
      makes core-level reuse harder.
    - Plain classes work in pure-Python contexts (services, tests,
      pricing) without Django loaded.
    - The `CHOICES` list is idiomatic Django and works with
      `CharField(choices=...)` and `TextChoices`-style migrations.

If you later want strict typing, migrate individual enums to
`enum.StrEnum` — the `choices_list` helper works with both.
"""

from __future__ import annotations

from typing import Iterable


def choices_list(
    pairs: Iterable[tuple[str, str]],
) -> list[tuple[str, str]]:
    """
    Normalise a CHOICES list.

    Accepts any iterable of (value, label) tuples and returns a new
    list. Exists so sub-modules can build CHOICES from other
    collections without duplicating the type annotation.
    """
    return list(pairs)