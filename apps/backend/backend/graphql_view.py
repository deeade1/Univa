# apps/backend/backend/graphql_view.py

"""
GraphQL view with full traceback logging for underlying errors.

Wraps graphene_django.views.GraphQLView so that when a resolver raises
an exception that Graphene turns into a GraphQLError, the original
Python traceback is logged with line numbers.
"""

import logging
import traceback

from graphene_django.views import GraphQLView


logger = logging.getLogger("graphql.errors")


class LoggingGraphQLView(GraphQLView):
    """GraphQLView that logs underlying exception tracebacks."""

    def execute_graphql_request(self, *args, **kwargs):
        result = super().execute_graphql_request(*args, **kwargs)

        if result is None or not getattr(result, "errors", None):
            return result

        for error in result.errors:
            logger.error("GraphQL error: %s", error)

            original = getattr(error, "original_error", None)
            if original is None:
                continue

            tb = "".join(
                traceback.format_exception(
                    type(original),
                    original,
                    original.__traceback__,
                )
            )
            logger.error(
                "Original exception traceback:\n%s",
                tb,
            )

        return result