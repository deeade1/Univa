# apps/backend/accounts/services/account.py

from django.db import transaction

from accounts.services.roles import assign_default_roles


@transaction.atomic
def provision_new_account(
    user,
    *,
    assigned_by=None,
):
    """
    Perform post-registration account provisioning.

    This is the orchestration layer.
    """

    assign_default_roles(
        user,
        assigned_by=assigned_by,
    )

    return user