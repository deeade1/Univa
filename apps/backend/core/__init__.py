from django.conf import settings
from django.core.files.storage import Storage, FileSystemStorage
from django.utils.functional import LazyObject
from django.utils.module_loading import import_string


class JobStatus:
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    DELETED = "deleted"

    CHOICES = [
        (PENDING, "Pending"),
        (SUCCESS, "Success"),
        (FAILED, "Failed"),
        (DELETED, "Deleted"),
    ]


class TimePeriodType:
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"

    CHOICES = [(DAY, "Day"), (WEEK, "Week"), (MONTH, "Month"), (YEAR, "Year")]


class EventDeliveryStatus:
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

    CHOICES = [
        (PENDING, "Pending"),
        (SUCCESS, "Success"),
        (FAILED, "Failed"),
    ]




def _get_private_storage_class(import_path=None):
    """
    Returns the storage class.
    1. Uses explicit import_path if provided
    2. Falls back to settings.DEFAULT_FILE_STORAGE if defined
    3. Otherwise defaults to FileSystemStorage
    """
    path = import_path or getattr(settings, "DEFAULT_FILE_STORAGE", None)
    if path:
        return import_string(path)
    return FileSystemStorage


class PrivateStorage(LazyObject):
    """
    Lazy wrapper around a Django Storage class.
    Ensures storage is only loaded when first accessed.
    """
    def _setup(self):
        storage_class = _get_private_storage_class()
        self._wrapped = storage_class()


# Singleton instance
private_storage: Storage = PrivateStorage()
