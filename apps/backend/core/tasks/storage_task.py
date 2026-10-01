import logging
import requests
from celery import Task, shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import connections
from django.db.models import Exists, OuterRef
from django.utils import timezone
from firebase_admin import messaging
from twilio.rest import Client
from backend.celery import app
from core.connection import allow_writer

#from .models import EventDelivery, EventPayload
from celery import shared_task
from django.apps import apps


from django.conf import settings
from django.core.files.storage import Storage, FileSystemStorage
from django.utils.functional import LazyObject
from django.utils.module_loading import import_string




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

logger = logging.getLogger(__name__)



task_logger: logging.Logger = get_task_logger(__name__)


'''class RestrictWriterDBTask(Task):
    """Celery task that checks usage of unrestricted queries to the writer database.

    A base class for Celery tasks that protects from inexplicit usages of DB queries
    to the writer DB. Depending on the `CELERY_RESTRICT_WRITER_METHOD` setting, the task
    will either log a warning (suitable for production) or raise an exception (suitable
    for tests).

    The `CELERY_RESTRICT_WRITER_METHOD` setting should point to one of the following:
    - `core.db.connection.log_writer_usage` - logs a warning
    - `core.db.connection.restrict_writer` - raises an exception
    """

    def __call__(self, *args, **kwargs):
        from django.utils.module_loading import import_string

        func_path = settings.CELERY_RESTRICT_WRITER_METHOD
        if not func_path:
            return

        try:
            wrapper_fun = import_string(func_path)
        except ImportError:
            task_logger.error(
                f"Could not import the function {func_path}. "
                f"Check if the path is correct."
            )
            return super().__call__(*args, **kwargs)

        with connections[settings.DATABASE_CONNECTION_DEFAULT_NAME].execute_wrapper(
            wrapper_fun
        ):
            return super().__call__(*args, **kwargs)


# Batch size was tested on db with 1mln payloads and deliveries, each delivery
# had multiple attempts. One task took less than 0,5 second, memory usage didn't raise
# more than 100 MB.
BATCH_SIZE = 1000
@app.task
def delete_event_payloads_task(expiration_date=None):
    expiration_date = (
        expiration_date
        or timezone.now() + settings.EVENT_PAYLOAD_DELETE_TASK_TIME_LIMIT
    )
    delete_period = timezone.now() - settings.EVENT_PAYLOAD_DELETE_PERIOD
    valid_deliveries = EventDelivery.objects.filter(created_at__gt=delete_period)
    payloads_to_delete = (
        EventPayload.objects.using(settings.DATABASE_CONNECTION_REPLICA_NAME)
        .filter(~Exists(valid_deliveries.filter(payload_id=OuterRef("id"))))
        .order_by("-pk")
    )
    ids = list(payloads_to_delete.values_list("pk", flat=True)[:BATCH_SIZE])
    if ids:
        if expiration_date > timezone.now():
            qs = EventPayload.objects.filter(pk__in=ids)
            files_to_delete = [
                event_payload.payload_file.name
                for event_payload in qs.using(settings.DATABASE_CONNECTION_REPLICA_NAME)
                if event_payload.payload_file
            ]
            with allow_writer():
                qs.delete()
            delete_files_from_private_storage_task.delay(files_to_delete)
            delete_event_payloads_task.delay(expiration_date)
        else:
            task_logger.error("Task invocation time limit reached, aborting task")'''


'''@shared_task(
    bind=True,
    autoretry_for=(GeocoderServiceError, GeocoderTimedOut),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def reverse_geocode_location(
    self,
    app_label,
    model_name,
    object_id,
):
    """
    Reverse geocode an object's coordinates and update its address.
    """

    Model = apps.get_model(app_label, model_name)

    try:
        obj = Model.objects.get(pk=object_id)

        if obj.latitude is None or obj.longitude is None:
            return

        location = geolocator.reverse(
            (float(obj.latitude), float(obj.longitude)),
            exactly_one=True,
            timeout=10,
        )

        if not location:
            return

        obj.location = location.address

        obj.save(update_fields=["location"])

        logger.info(
            "Updated address for %s:%s",
            model_name,
            object_id,
        )

    except Model.DoesNotExist:
        logger.warning(
            "%s %s no longer exists",
            model_name,
            object_id,
        )

    except Exception as exc:
        logger.exception(exc)
        raise'''     
        
@app.task
def delete_from_storage_task(path):
    default_storage.delete(path)
    
@app.task
def delete_files_from_storage_task(paths):
    for path in paths:
        default_storage.delete(path)


@app.task
def delete_files_from_private_storage_task(paths):
    for path in paths:
        private_storage.delete(path)

@shared_task(bind=True, queue='notifications')
def send_sms_notification(self, phone_number, message):
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
    except Exception as e:
        self.retry(exc=e, countdown=60)



@shared_task(bind=True, queue='notifications', max_retries=3, default_retry_delay=60)
def send_push_notification(self, device_token, title, body, data=None):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=device_token,
        data=data or {}
    )
    try:
        messaging.send(message)
    except Exception as e:
        raise self.retry(exc=e)  # Proper retry with `self`


@shared_task(queue='notifications')
def send_websocket_notification(user_id, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "notification.message",
            "message": message
        }
    )




