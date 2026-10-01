"""
Univa JSON serialization utilities.

This module provides the canonical JSON encoders used by Univa.

Architecture
------------

Pricing is owned by:

    core.pricing

The project MUST NOT depend on the third-party ``prices`` package.

This module therefore imports Money exclusively from:

    core.pricing

HTMLSafeJSON is implemented locally and provides HTML-safe JSON
serialization without introducing an unnecessary third-party
dependency such as ``draftjs-sanitizer``.
"""

from __future__ import annotations

from typing import Any

from django.core.serializers.json import DjangoJSONEncoder
from django.core.serializers.json import Serializer as JsonSerializer
from measurement.measures import Weight

from core.pricing import Money


MONEY_TYPE = "Money"


class Serializer(JsonSerializer):
    """
    Django JSON serializer using Univa's custom JSON encoder.

    This serializer preserves Django's normal serialization behavior
    while ensuring Univa-specific values such as Money and Weight are
    serialized consistently.
    """

    def _init_options(self) -> None:
        super()._init_options()
        self.json_kwargs["cls"] = CustomJsonEncoder


class CustomJsonEncoder(DjangoJSONEncoder):
    """
    JSON encoder for Univa-specific value types.

    Supported custom values:

    - core.pricing.Money
    - measurement.measures.Weight

    Everything else is delegated to DjangoJSONEncoder.
    """

    def default(self, obj: Any) -> Any:
        """
        Serialize values that are not natively JSON serializable.
        """

        if isinstance(obj, Money):
            return {
                "_type": MONEY_TYPE,
                "amount": str(obj.amount),
                "currency": obj.currency,
            }

        # Mirror django_measurement.MeasurementField.value_to_string.
        if isinstance(obj, Weight):
            return f"{obj.value}:{obj.unit}"

        return super().default(obj)


class HTMLSafeJSON(CustomJsonEncoder):
    """
    JSON encoder suitable for embedding JSON inside HTML.

    The JSON output is generated normally and then dangerous HTML
    characters are represented using Unicode escapes.

    For example:

        <script>alert(1)</script>

    becomes:

        \\u003cscript\\u003ealert(1)\\u003c/script\\u003e

    The following characters are escaped:

    - <
    - >
    - &
    - '

    Escaping is performed on the generated JSON text rather than
    modifying Python's private json encoder internals.
    """

    HTML_ESCAPE_MAP = str.maketrans(
        {
            "<": "\\u003c",
            ">": "\\u003e",
            "&": "\\u0026",
            "'": "\\u0027",
        }
    )

    def encode(self, obj: Any) -> str:
        """
        Encode an object as JSON and make the resulting JSON HTML-safe.
        """

        encoded = super().encode(obj)

        return encoded.translate(self.HTML_ESCAPE_MAP)

    def iterencode(
        self,
        obj: Any,
        _one_shot: bool = False,
    ):
        """
        Incrementally encode an object while applying HTML-safe escaping.

        This keeps behavior consistent whether json.dumps() uses
        encode() or iterencode().
        """

        for chunk in super().iterencode(obj, _one_shot):
            yield chunk.translate(self.HTML_ESCAPE_MAP)

