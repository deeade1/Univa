# graphq/ecommerce/access.py

from django.db.models import Q


def user_can_see_all_orders(user) -> bool:
    return bool(user and user.is_authenticated and user.is_staff)


def user_visible_orders_qs(base_qs, user):
    if user is None or not user.is_authenticated:
        return base_qs.none()
    if user_can_see_all_orders(user):
        return base_qs
    return base_qs.filter(Q(user=user) | Q(user_email=user.email))