"""
Focused tests for Univa JSON serialization.

This test deliberately loads json_serializer.py directly so the
serializer can be tested independently of unrelated core.utils
imports.
"""

import importlib.util
import json
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parent
    / "core"
    / "utils"
    / "json_serializer.py"
)


spec = importlib.util.spec_from_file_location(
    "json_serializer",
    MODULE_PATH,
)

if spec is None or spec.loader is None:
    raise RuntimeError(
        f"Unable to load serializer module: {MODULE_PATH}"
    )


module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


HTMLSafeJSON = module.HTMLSafeJSON
CustomJsonEncoder = module.CustomJsonEncoder


from core.pricing import Money


print("HTMLSafeJSON import: OK")
print("CustomJsonEncoder import: OK")
print("core.pricing.Money import: OK")


payload = {
    "html": "<script>alert(1)</script>",
    "quote": "it's safe",
    "amp": "A & B",
    "money": Money("1500.00", "NGN"),
}


encoded = json.dumps(
    payload,
    cls=HTMLSafeJSON,
)


print("\nSerialized JSON:")
print(encoded)


assert "\\u003cscript\\u003e" in encoded
assert "\\u003c/script\\u003e" in encoded
assert "\\u0027" in encoded
assert "\\u0026" in encoded

assert '"_type": "Money"' in encoded
assert '"amount": "1500.00"' in encoded
assert '"currency": "NGN"' in encoded

assert "<script>" not in encoded
assert "</script>" not in encoded

print("\nJSON serializer verification: PASS")

