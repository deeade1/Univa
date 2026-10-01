from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from audit.constants import AUDIT_ACTIONS
from audit.models import AuditLog


def record_audit(
    *,
    action: str,
    actor=None,
    target_user=None,
    data: Mapping[str, Any] | None = None,
) -> AuditLog:
    """
    Persist a canonical audit record.

    AuditLog creation must go through this service rather than being
    performed directly by domain applications.
    """

    if not action:
        raise ValueError("Audit action is required.")

    if action not in AUDIT_ACTIONS:
        raise ValueError(
            f"Unknown audit action: {action!r}. "
            "Use an action from audit.constants.AuditAction."
        )

    if data is not None and not isinstance(data, Mapping):
        raise TypeError(
            "Audit data must be a mapping or None."
        )

    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_user=target_user,
        data=(
            dict(data)
            if data is not None
            else None
        ),
    )


def audit(
    *,
    action: str,
    actor=None,
    target_user=None,
    **data: Any,
) -> AuditLog:
    """
    Convenience API for recording an audit action.
    """

    return record_audit(
        action=action,
        actor=actor,
        target_user=target_user,
        data=data or None,
    )