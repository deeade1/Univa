"""
GraphQL error formatting for Univa.
"""

import json
import logging
import traceback

from django.conf import settings
from django.core.exceptions import ValidationError
from graphene_django.views import GraphQLView
from graphql import GraphQLError
from graphql.error import GraphQLSyntaxError

from univa_jwt.exceptions import UnivaJWTBaseException


logger = logging.getLogger("univa_jwt")


class InternalServerError(Exception):
    default_message = (
        "A server error occurred. "
        "Please try again later."
    )
    code = 500


def format_internal_error(
    error,
    code=None,
):
    response = {
        "message": str(error)
        or getattr(
            error,
            "default_message",
            "An error occurred.",
        ),
        "code": code
        or getattr(
            error,
            "code",
            500,
        ),
    }

    if settings.DEBUG:
        response["exception"] = (
            type(error).__name__
        )

        if error.__traceback__:
            response["trace"] = traceback.format_list(
                traceback.extract_tb(
                    error.__traceback__
                )
            )

    logger.info(
        json.dumps(
            response,
            default=str,
        )
    )

    return response


class PatchedGraphQLView(GraphQLView):

    @staticmethod
    def format_error(original_error):
        error = getattr(
            original_error,
            "original_error",
            original_error,
        )

        if isinstance(
            error,
            UnivaJWTBaseException,
        ):
            return format_internal_error(
                error,
                code=error.code,
            )

        if isinstance(
            error,
            ValidationError,
        ):
            return format_internal_error(
                error,
                code=400,
            )

        if isinstance(
            error,
            GraphQLSyntaxError,
        ):
            return format_internal_error(
                error,
                code=400,
            )

        if settings.DEBUG:
            return format_internal_error(error)

        return format_internal_error(
            InternalServerError(),
            code=500,
        )