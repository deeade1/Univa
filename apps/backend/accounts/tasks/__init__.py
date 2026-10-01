# apps/backend/accounts/tasks/__init__.py

"""
Accounts Celery tasks.

ARCHITECTURE
------------

The accounts task package exposes asynchronous orchestration only.

Email-verification business logic belongs exclusively to:

    accounts.email_service

Role maintenance and lifecycle tasks belong to:

    accounts.tasks.maintenance

This package intentionally re-exports only tasks that actually exist.

Do not retain legacy imports here. Stale task exports can cause unrelated
modules, including GraphQL mutations and tests, to fail during import.

Current task boundaries
-----------------------

Email verification:

    accounts.tasks.email.send_confirmation_email_task
        │
        ▼
    accounts.email_service.resend_confirmation_email()

Maintenance / role lifecycle:

    accounts.tasks.maintenance.deactivate_expired_roles
    accounts.tasks.maintenance.assign_default_roles
    accounts.tasks.maintenance.process_role_change

This module must remain a lightweight public task registry.
"""

from __future__ import annotations


# =============================================================================
# EMAIL TASKS
# =============================================================================

from .email import (
    send_confirmation_email_task,
)


# =============================================================================
# MAINTENANCE TASKS
# =============================================================================

from .maintenance import (
    assign_default_roles,
    deactivate_expired_roles,
    process_role_change,
)


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Email
    "send_confirmation_email_task",

    # Maintenance / roles
    "assign_default_roles",
    "deactivate_expired_roles",
    "process_role_change",
]
