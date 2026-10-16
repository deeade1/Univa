# graphq/core/fields.py

"""
Custom Graphene-Django fields.

`AccessControlledFilterConnectionField` — applies a user-based
queryset filter before the FilterSet's own filtering.
"""

from __future__ import annotations

from graphene_django.filter import DjangoFilterConnectionField


class AccessControlledFilterConnectionField(DjangoFilterConnectionField):
    """
    A DjangoFilterConnectionField that applies an access-control
    filter before the FilterSet's own filters.

    Pass `get_base_queryset` — a callable `(info) -> QuerySet` that
    returns the queryset this user is allowed to see. The FilterSet
    then narrows that further.
    """

    def __init__(self, *args, get_base_queryset=None, **kwargs):
        self.get_base_queryset = get_base_queryset
        super().__init__(*args, **kwargs)

    def resolve_queryset(
        self,
        connection,
        iterable,
        info,
        args,
        filtering_args,
        filterset_class,
    ):
        qs = iterable

        if self.get_base_queryset is not None:
            qs = self.get_base_queryset(info)

        # Now apply the FilterSet as the parent would.
        filter_kwargs = {
            k: v
            for k, v in args.items()
            if k in filtering_args
        }
        return super().resolve_queryset(
            connection,
            qs,
            info,
            args,
            filtering_args,
            filterset_class,
        )