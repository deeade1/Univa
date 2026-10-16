# graphq/core/types/scalars.py

"""
Custom GraphQL scalars for the Univa schema.

JSONField on Django models is exposed by Graphene-Django as JSONString
by default, which serializes a parsed dict as a JSON-encoded *string*.
Clients then have to json.loads() the response. This is inconsistent
with how JSON APIs typically work.

These scalars solve that: the value round-trips as a JSON object/array
on the wire, not as a string containing JSON.
"""

import graphene
from graphene.types.generic import GenericScalar


# `GenericScalar` already does exactly what we want — it accepts and
# returns any JSON-serializable Python value (dict, list, str, int,
# float, bool, None) and serializes it to its natural GraphQL form.
#
# We alias it as `JSONScalar` to make the intent explicit at the call
# site and give future maintainers a single place to change the
# underlying implementation if we ever need to.
JSONScalar = GenericScalar


__all__ = ["JSONScalar"]