"""
GraphQL authentication decorators.

These decorators support both standard Graphene 3 resolvers and
relay.ClientIDMutation classmethods.

Standard Graphene resolver signature:

    resolver(root, info, **kwargs)

Graphene Relay ClientIDMutation signature:

    mutate_and_get_payload(cls, root, info, **kwargs)

Authentication and authorization are transport-layer concerns and are
evaluated exclusively from:

    info.context.user
"""

from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable, Union

from univa_jwt.exceptions import PermissionDenied, WrongUsage


# =============================================================================
# Message constants
# =============================================================================

_UNAUTHENTICATED = [
    {
        "message": "Authentication required.",
    }
]

_UNAUTHORIZED = [
    {
        "message": "You do not have permission to perform this action.",
    }
]

_NOT_VERIFIED = [
    {
        "message": "Email verification required.",
    }
]

_SECONDARY_EMAIL_REQUIRED = [
    {
        "message": "Secondary email is required.",
    }
]

_INVALID_PASSWORD = {
    "password": "Invalid password.",
}


# =============================================================================
# Context helper
# =============================================================================


def _get_user_from_info(info: Any) -> Any:
    """
    Return the authenticated Django user from Graphene's resolver info.

    Graphene 3 provides:

        info.context.user
    """

    context = getattr(
        info,
        "context",
        None,
    )

    return getattr(
        context,
        "user",
        None,
    )


# =============================================================================
# Callable signature helpers
# =============================================================================


def _is_client_id_mutation_callable(func: Callable) -> bool:
    """
    Determine whether ``func`` follows the Relay ClientIDMutation
    classmethod signature.

    Expected signature:

        func(cls, root, info, **kwargs)

    This is deliberately based on the callable's declared signature rather
    than scanning runtime positional arguments for GraphQLResolveInfo.
    """

    try:
        parameters = list(
            inspect.signature(func).parameters.values()
        )
    except (TypeError, ValueError):
        return False

    if len(parameters) < 3:
        return False

    first = parameters[0]
    second = parameters[1]
    third = parameters[2]

    return (
        first.name in {"cls", "klass", "mutation_cls"}
        and second.name in {"root", "parent"}
        and third.name == "info"
    )


# =============================================================================
# Context decorator
# =============================================================================


def context(func: Callable) -> Callable:
    """
    Inject the GraphQL context/request into a resolver.

    Public Graphene resolver:

        resolver(root, info, **kwargs)

    Wrapped callable:

        func(request, root, info, **kwargs)
    """

    @wraps(func)
    def wrapper(
        root,
        info,
        *args,
        **kwargs,
    ):
        context_obj = getattr(
            info,
            "context",
            None,
        )

        if context_obj is None:
            raise ValueError(
                "GraphQL context is required."
            )

        return func(
            context_obj,
            root,
            info,
            *args,
            **kwargs,
        )

    return wrapper


# =============================================================================
# User test decorator
# =============================================================================


def user_passes_test(
    test_func: Callable[[Any], bool],
) -> Callable:
    """
    Allow execution only when the current GraphQL user passes ``test_func``.

    Supports both:

        resolver(root, info, **kwargs)

    and Relay ClientIDMutation:

        mutate_and_get_payload(cls, root, info, **kwargs)

    The GraphQLResolveInfo object is obtained from its declared ``info``
    parameter. Positional arguments are not searched heuristically.
    """

    def decorator(func: Callable) -> Callable:

        if _is_client_id_mutation_callable(func):

            @wraps(func)
            def mutation_wrapper(
                cls,
                root,
                info,
                *args,
                **kwargs,
            ):
                user = _get_user_from_info(info)

                if user and test_func(user):
                    return func(
                        cls,
                        root,
                        info,
                        *args,
                        **kwargs,
                    )

                raise PermissionDenied(
                    _UNAUTHORIZED[0]["message"]
                )

            return mutation_wrapper

        @wraps(func)
        def resolver_wrapper(
            root,
            info,
            *args,
            **kwargs,
        ):
            user = _get_user_from_info(info)

            if user and test_func(user):
                return func(
                    root,
                    info,
                    *args,
                    **kwargs,
                )

            raise PermissionDenied(
                _UNAUTHORIZED[0]["message"]
            )

        return resolver_wrapper

    return decorator


# =============================================================================
# Authentication / authorization decorators
# =============================================================================


login_required = user_passes_test(
    lambda user: user.is_authenticated
)


staff_member_required = user_passes_test(
    lambda user: (
        user.is_authenticated
        and user.is_active
        and user.is_staff
    )
)


superuser_required = user_passes_test(
    lambda user: (
        user.is_authenticated
        and user.is_active
        and user.is_superuser
    )
)


def permission_required(
    permission: Union[str, list[str]],
):
    """
    Require one or more Django permissions.
    """

    permissions = (
        [permission]
        if isinstance(permission, str)
        else permission
    )

    return user_passes_test(
        lambda user: user.has_perms(
            permissions
        )
    )


# =============================================================================
# Authenticated required
# =============================================================================


def authenticated_required(func: Callable) -> Callable:
    """
    Require an authenticated user.

    Unlike ``login_required``, this decorator returns the mutation's normal
    failure payload instead of raising PermissionDenied.

    This decorator is intended for Relay ClientIDMutation methods.
    """

    @wraps(func)
    def wrapper(
        cls,
        root,
        info,
        **kwargs,
    ):
        user = _get_user_from_info(info)

        if not user or not user.is_authenticated:
            return cls(
                success=False,
                errors=_UNAUTHENTICATED,
            )

        return func(
            cls,
            root,
            info,
            **kwargs,
        )

    return wrapper


# =============================================================================
# Verification required
# =============================================================================


def verification_required(func: Callable) -> Callable:
    """
    Require an authenticated and verified account.

    Intended for Relay ClientIDMutation methods.
    """

    @wraps(func)
    @authenticated_required
    def wrapper(
        cls,
        root,
        info,
        **kwargs,
    ):
        user = _get_user_from_info(info)

        status = getattr(
            user,
            "status",
            None,
        )

        if not getattr(
            status,
            "verified",
            False,
        ):
            return cls(
                success=False,
                errors=_NOT_VERIFIED,
            )

        return func(
            cls,
            root,
            info,
            **kwargs,
        )

    return wrapper


# =============================================================================
# Secondary email required
# =============================================================================


def secondary_email_required(func: Callable) -> Callable:
    """
    Require an authenticated, verified account with a secondary email.

    Intended for Relay ClientIDMutation methods.
    """

    @wraps(func)
    @verification_required
    def wrapper(
        cls,
        root,
        info,
        **kwargs,
    ):
        user = _get_user_from_info(info)

        status = getattr(
            user,
            "status",
            None,
        )

        if not getattr(
            status,
            "secondary_email",
            None,
        ):
            return cls(
                success=False,
                errors=_SECONDARY_EMAIL_REQUIRED,
            )

        return func(
            cls,
            root,
            info,
            **kwargs,
        )

    return wrapper


# =============================================================================
# Password confirmation required
# =============================================================================


def password_confirmation_required(func: Callable) -> Callable:
    """
    Require the authenticated user's current password.

    Intended for Relay ClientIDMutation methods.
    """

    @wraps(func)
    @authenticated_required
    def wrapper(
        cls,
        root,
        info,
        **kwargs,
    ):
        user = _get_user_from_info(info)

        password = kwargs.get(
            "password_confirmation"
        )

        if not password:
            return cls(
                success=False,
                errors=_INVALID_PASSWORD,
            )

        if not user.check_password(password):
            return cls(
                success=False,
                errors=_INVALID_PASSWORD,
            )

        return func(
            cls,
            root,
            info,
            **kwargs,
        )

    return wrapper


# =============================================================================
# Password match required
# =============================================================================


def password_match_required(func: Callable) -> Callable:
    """
    Require the authenticated user's current password.

    The mutation must provide either:

        password
        old_password

    Intended for Relay ClientIDMutation methods.
    """

    @wraps(func)
    @authenticated_required
    def wrapper(
        cls,
        root,
        info,
        **kwargs,
    ):
        user = _get_user_from_info(info)

        field_name = next(
            (
                key
                for key in kwargs
                if key in (
                    "password",
                    "old_password",
                )
            ),
            None,
        )

        if field_name is None:
            raise WrongUsage(
                "@password_match_required requires "
                "'password' or 'old_password'."
            )

        password = kwargs[field_name]

        if not user.check_password(password):
            return cls(
                success=False,
                errors={
                    field_name: _INVALID_PASSWORD,
                },
            )

        return func(
            cls,
            root,
            info,
            **kwargs,
        )

    return wrapper


# =============================================================================
# Face verification required
# =============================================================================


def face_verified_required(func: Callable) -> Callable:
    """
    Require a successfully verified face.

    Face verification remains an Accounts/Biometrics concern.

    This decorator only checks the established user relation and does not
    implement biometric verification logic.

    Intended for Relay ClientIDMutation methods.
    """

    @wraps(func)
    @authenticated_required
    def wrapper(
        cls,
        root,
        info,
        **kwargs,
    ):
        user = _get_user_from_info(info)

        verification = getattr(
            user,
            "face_verification",
            None,
        )

        if not verification or not verification.is_verified:
            return cls(
                success=False,
                errors={
                    "message": "Face verification required.",
                },
            )

        return func(
            cls,
            root,
            info,
            **kwargs,
        )

    return wrapper
