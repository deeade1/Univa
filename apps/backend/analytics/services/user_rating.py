# analytics/services/user_rating.py

from django.db.models import Avg


def calculate_user_rating(user):
    from ecommerce.models import Order
    from transport.models import ServiceRequest

    transport = (
        ServiceRequest.objects.filter(
            customer=user
        )
        .aggregate(
            Avg("customer_rating")
        )
        ["customer_rating__avg"]
        or 0
    )

    commerce = (
        Order.objects.filter(
            customer=user
        )
        .aggregate(
            Avg("seller_rating")
        )
        ["seller_rating__avg"]
        or 0
    )

    rating = round(
        (transport + commerce) / 2,
        2,
    )

    profile = user.profile
    profile.rating = rating
    profile.save(update_fields=["rating"])

    return rating