from django.db import models, transaction
from django.db.models import F, Max


class SortableModel(models.Model):
    """
    Abstract base for models whose rows can be reordered within a
    parent scope.

    Subclasses must implement `get_ordering_queryset()` to return
    the sibling rows they are ordered against. `sort_order` is
    assigned on first save and renumbered on delete; the ordering
    scope is whatever the subclass returns, not the table as a
    whole.

    `sort_order` is `editable=False` so it is not exposed in admin
    forms, but it is deliberately not `blank=False`/`null=False` —
    callers may set it programmatically, and the field is nullable
    until first save.
    """

    sort_order = models.IntegerField(
        editable=False,
        db_index=True,
        null=True,
    )

    class Meta:
        abstract = True

    def get_ordering_queryset(self):
        raise NotImplementedError("Unknown ordering queryset")

    @staticmethod
    def get_max_sort_order(qs):
        existing_max = qs.aggregate(Max("sort_order"))
        return existing_max.get("sort_order__max")

    def save(self, *args, **kwargs):
        # Only assign a sort_order if one has not been set.
        #
        # The guard is on `sort_order`, not on `pk`. Django evaluates
        # `default=uuid4` (and any other PK default) at instance
        # construction, so `self.pk is None` is False for every UUID-
        # keyed model before save ever runs. Guarding on the field we
        # are about to assign is correct for every PK type, and it
        # preserves an explicitly-set sort_order if the caller
        # provided one.
        if self.sort_order is None:
            qs = self.get_ordering_queryset()
            existing_max = self.get_max_sort_order(qs)
            self.sort_order = 0 if existing_max is None else existing_max + 1

        super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        if self.sort_order is not None:
            qs = self.get_ordering_queryset()
            qs.filter(sort_order__gt=self.sort_order).update(
                sort_order=F("sort_order") - 1
            )
        super().delete(*args, **kwargs)