"""
Staff GraphQL query modules.
"""

from .department import DepartmentQuery
from .position import PositionQuery
from .staff_member import StaffMemberQuery

__all__ = [
    "DepartmentQuery",
    "PositionQuery",
    "StaffMemberQuery",
]