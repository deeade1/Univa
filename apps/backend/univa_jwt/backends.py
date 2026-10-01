"""
Django authentication backend for Univa.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from univa_jwt.authentication import JWTAuthenticationService
from univa_jwt.exceptions import InvalidCredentials


User = get_user_model()


class UnivaAuthenticationBackend(ModelBackend):
    """
    Password authentication backend.

    JWT authentication itself is deliberately handled by
    JWTAuthenticationService.
    """

    def authenticate(
        self,
        request,
        username=None,
        password=None,
        email=None,
        phone_number=None,
        **kwargs,
    ):
        identifier = email or username

        if not password:
            return None

        if identifier:
            user = User.objects.filter(
                email__iexact=identifier
            ).first()

            if user and user.check_password(password):
                if user.is_active:
                    return user

            return None

        if phone_number:
            user = User.objects.filter(
                phone_number=phone_number
            ).first()

            if user and user.check_password(password):
                if user.is_active:
                    return user

        return None