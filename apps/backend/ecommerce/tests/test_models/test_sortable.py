# apps/backend/ecommerce/tests/models/test_sortable.py

"""
Tests for core.models.sortable.SortableModel.

The behavior we care about most:

    - sort_order is assigned on first save
    - sort_order is NOT reassigned on subsequent saves
    - sort_order is NOT reassigned if the caller set it explicitly
    - sort_order is assigned correctly for models with a UUID PK
      (the regression this test exists to prevent)
    - deleting a row renumbers its siblings
"""

from uuid import uuid4

from django.db import models, connection
from django.test import TestCase

from core.models.sortable import SortableModel


# ----------------------------------------------------------------------
# Test-only models
# ----------------------------------------------------------------------
#
# SortableModel is abstract. To exercise both PK flavors we define two
# concrete subclasses here, each implementing get_ordering_queryset the
# way a production subclass would. They are unmanaged so no migration
# is required — the test creates and drops their tables directly.


class AutoPkSortable(SortableModel):
    """Sortable with the implicit AutoField PK."""

    name = models.CharField(max_length=32)

    class Meta:
        app_label = "ecommerce"
        managed = False
        db_table = "test_sortable_auto_pk"

    def get_ordering_queryset(self):
        return AutoPkSortable.objects.all()


class UuidPkSortable(SortableModel):
    """
    Sortable with a UUID PK.

    This is the regression case. The old `if self.pk is None` guard
    in SortableModel.save() never fired for this shape because
    `default=uuid4` runs at construction.
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=32)

    class Meta:
        app_label = "ecommerce"
        managed = False
        db_table = "test_sortable_uuid_pk"

    def get_ordering_queryset(self):
        return UuidPkSortable.objects.all()


class SortableModelTests(TestCase):
    """
    Behavioral tests for SortableModel.

    Uses raw DDL to create the two unmanaged test tables, because
    registering migrations for test-only models is more machinery than
    the behavior is worth.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_sortable_auto_pk (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(32) NOT NULL,
                    sort_order INTEGER
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_sortable_uuid_pk (
                    id UUID PRIMARY KEY,
                    name VARCHAR(32) NOT NULL,
                    sort_order INTEGER
                )
            """)

    @classmethod
    def tearDownClass(cls):
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_sortable_auto_pk")
            cursor.execute("DROP TABLE IF EXISTS test_sortable_uuid_pk")

        super().tearDownClass()

    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE test_sortable_auto_pk")
            cursor.execute("TRUNCATE test_sortable_uuid_pk")

    # ------------------------------------------------------------------
    # AutoField PK
    # ------------------------------------------------------------------

    def test_auto_pk_first_save_assigns_zero(self):
        row = AutoPkSortable.objects.create(name="first")

        self.assertEqual(row.sort_order, 0)

    def test_auto_pk_second_save_assigns_next(self):
        AutoPkSortable.objects.create(name="first")
        second = AutoPkSortable.objects.create(name="second")

        self.assertEqual(second.sort_order, 1)

    def test_auto_pk_second_save_does_not_reassign_sort_order(self):
        row = AutoPkSortable.objects.create(name="first")

        row.name = "renamed"
        row.save()

        row.refresh_from_db()
        self.assertEqual(row.sort_order, 0)

    def test_auto_pk_explicit_sort_order_is_preserved(self):
        row = AutoPkSortable.objects.create(name="explicit", sort_order=42)

        self.assertEqual(row.sort_order, 42)

    # ------------------------------------------------------------------
    # UUID PK — the regression case
    # ------------------------------------------------------------------

    def test_uuid_pk_first_save_assigns_zero(self):
        row = UuidPkSortable.objects.create(name="first")

        self.assertEqual(row.sort_order, 0)

    def test_uuid_pk_second_save_assigns_next(self):
        """
        Regression test: with the old `if self.pk is None` guard,
        sort_order was never assigned for UUID-PK models, so both
        rows would have sort_order = None and the ordering would
        be undefined.
        """
        first = UuidPkSortable.objects.create(name="first")
        second = UuidPkSortable.objects.create(name="second")

        self.assertEqual(first.sort_order, 0)
        self.assertEqual(second.sort_order, 1)

    def test_uuid_pk_second_save_does_not_reassign_sort_order(self):
        row = UuidPkSortable.objects.create(name="first")

        row.name = "renamed"
        row.save()

        row.refresh_from_db()
        self.assertEqual(row.sort_order, 0)

    def test_uuid_pk_explicit_sort_order_is_preserved(self):
        row = UuidPkSortable.objects.create(name="explicit", sort_order=42)

        self.assertEqual(row.sort_order, 42)

    # ------------------------------------------------------------------
    # Delete renumbering
    # ------------------------------------------------------------------

    def test_delete_renumbers_siblings(self):
        a = AutoPkSortable.objects.create(name="a")
        b = AutoPkSortable.objects.create(name="b")
        c = AutoPkSortable.objects.create(name="c")

        a.delete()

        b.refresh_from_db()
        c.refresh_from_db()

        self.assertEqual(b.sort_order, 0)
        self.assertEqual(c.sort_order, 1)

    def test_delete_of_last_row_does_not_touch_siblings(self):
        AutoPkSortable.objects.create(name="a")
        b = AutoPkSortable.objects.create(name="b")

        b.delete()

        remaining = list(
            AutoPkSortable.objects.order_by("sort_order")
        )
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].sort_order, 0)