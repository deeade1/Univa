# accounts/services/profile_metrics.py

from django.db.models import Avg


def update_profile_metrics(profile, *, ratings=None):
    """
    Update Accounts-owned aggregate profile metrics.

    Domain applications provide their calculated metrics.
    Accounts does not import domain models.
    """
    ratings = ratings or {}

    values = [
        value
        for value in ratings.values()
        if value is not None
    ]

    if values:
        profile.rating = round(
            sum(values) / len(values),
            2,
        )

    profile.save(
        update_fields=["rating"],
    )

    return profile