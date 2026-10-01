"""
Staff GraphQL types.
"""

from .department import DepartmentNode
from .position import PositionNode
from .staff_member import StaffMemberNode

__all__ = [
    "DepartmentNode",
    "PositionNode",
    "StaffMemberNode",
]