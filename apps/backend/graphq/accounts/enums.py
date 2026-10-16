# graphq/accounts/enums.py

"""
GraphQL enum definitions for accounts.
"""

import graphene
from django_countries import countries

from graphq.core.utils import str_to_enum


CountryCodeEnum = graphene.Enum(
    "CountryCode",
    [(str_to_enum(country[0]), country[0]) for country in countries],
)


class StaffMemberStatus(graphene.Enum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"

    @property
    def description(self):
        if self == StaffMemberStatus.ACTIVE:
            return "User account has been activated."
        elif self == StaffMemberStatus.DEACTIVATED:
            return "User account has not been activated yet."
        return None