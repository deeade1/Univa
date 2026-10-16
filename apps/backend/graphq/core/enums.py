# graphq/core/enums.py

import graphene
from django.conf import settings

from ecommerce.models.constants import (
    AllocationStrategy,
    MarkAsPaidStrategy,
    TransactionFlowStrategy,
)
from core import JobStatus, TimePeriodType
from core.units import (
    AreaUnits,
    DistanceUnits,
    MeasurementUnits,
    VolumeUnits,
    WeightUnits,
)
from thumbnail import IconThumbnailFormat, ThumbnailFormat

# Domain enums from ecommerce/models/enums/order.py
from ecommerce.models.enums.order import (
    FulfillmentStatus,
    OrderAuthorizeStatus,
    OrderChargeStatus,
    OrderEvents,
    OrderEventsEmails,
    OrderGrantedRefundStatus,
    OrderOrigin,
    OrderStatus,
)

from .utils import str_to_enum


# =====================================================================
# SORT / TIME
# =====================================================================


class OrderDirection(graphene.Enum):
    ASC = ""
    DESC = "-"

    @property
    def description(self):
        # pylint: disable=no-member
        if self == OrderDirection.ASC:
            return "Specifies an ascending sort order."
        if self == OrderDirection.DESC:
            return "Specifies a descending sort order."
        raise ValueError(f"Unsupported enum value: {self.value}")


class ReportingPeriod(graphene.Enum):
    TODAY = "TODAY"
    THIS_MONTH = "THIS_MONTH"


# =====================================================================
# to_enum — legacy builder for CHOICES-based classes
# =====================================================================


def to_enum(enum_cls, *, type_name=None, **options) -> graphene.Enum:
    """Create a Graphene enum from a class containing a set of options.

    The target class must expose a `CHOICES` attribute: a list of
    (value, label) tuples.

    :param enum_cls:
        The class to build the enum from.
    :param type_name:
        The name of the type. Default is the class name + 'Enum'.
    :param options:
        - description: Contains the type description.
        - deprecation_reason: Contains the deprecation reason.
    :return: graphene.Enum
    """

    deprecation_reason = getattr(enum_cls, "__deprecation_reason__", None)
    if deprecation_reason:
        options.setdefault("deprecation_reason", deprecation_reason)

    type_name = type_name or (enum_cls.__name__ + "Enum")
    enum_data = [
        (str_to_enum(code.upper()), code)
        for code, name in enum_cls.CHOICES
    ]
    return graphene.Enum(type_name, enum_data, **options)


# =====================================================================
# LANGUAGE
# =====================================================================


LanguageCodeEnum = graphene.Enum(
    "LanguageCodeEnum",
    [
        (lang[0].replace("-", "_").upper(), lang[0])
        for lang in settings.LANGUAGES
    ],
)


# =====================================================================
# CORE ENUMS (built from CHOICES-based classes)
# =====================================================================


IconThumbnailFormatEnum = to_enum(
    IconThumbnailFormat,
    type_name="IconThumbnailFormatEnum",
    description=IconThumbnailFormat.__doc__,
)

JobStatusEnum = to_enum(JobStatus)
TimePeriodTypeEnum = to_enum(TimePeriodType)
ThumbnailFormatEnum = to_enum(ThumbnailFormat)
AllocationStrategyEnum = to_enum(AllocationStrategy)
MarkAsPaidStrategyEnum = to_enum(MarkAsPaidStrategy)
TransactionFlowStrategyEnum = to_enum(TransactionFlowStrategy)


# =====================================================================
# UNIT ENUMS
# =====================================================================


MeasurementUnitsEnum = to_enum(MeasurementUnits)
DistanceUnitsEnum = to_enum(DistanceUnits)
AreaUnitsEnum = to_enum(AreaUnits)
VolumeUnitsEnum = to_enum(VolumeUnits)
WeightUnitsEnum = to_enum(WeightUnits)

unit_enums = [
    DistanceUnitsEnum,
    AreaUnitsEnum,
    VolumeUnitsEnum,
    WeightUnitsEnum,
]


# =====================================================================
# ORDER ENUMS (built from CHOICES-based classes in
# ecommerce/models/enums/order.py)
# =====================================================================


OrderStatusEnum = to_enum(
    OrderStatus,
    type_name="OrderStatusEnum",
)

OrderOriginEnum = to_enum(
    OrderOrigin,
    type_name="OrderOriginEnum",
)

OrderAuthorizeStatusEnum = to_enum(
    OrderAuthorizeStatus,
    type_name="OrderAuthorizeStatusEnum",
)

OrderChargeStatusEnum = to_enum(
    OrderChargeStatus,
    type_name="OrderChargeStatusEnum",
)

OrderGrantedRefundStatusEnum = to_enum(
    OrderGrantedRefundStatus,
    type_name="OrderGrantedRefundStatusEnum",
)

FulfillmentStatusEnum = to_enum(
    FulfillmentStatus,
    type_name="FulfillmentStatusEnum",
)

OrderEventsEnum = to_enum(
    OrderEvents,
    type_name="OrderEventsEnum",
)

OrderEventsEmailsEnum = to_enum(
    OrderEventsEmails,
    type_name="OrderEventsEmailsEnum",
)


# =====================================================================
# Note on OrderErrorCodeEnum
# =====================================================================
#
# `OrderErrorCodeEnum` is intentionally NOT defined here.
#
# It is defined in `graphq/ecommerce/types/errors.py`, next to the
# `OrderError` type that uses it, to avoid two competing definitions
# of the same GraphQL type name.
#
# `OrderErrorCode` is a Python `enum.Enum` (not a CHOICES-based
# class), so it is built with `graphene.Enum.from_enum` rather than
# `to_enum`.


__all__ = [
    # Sort / time
    "OrderDirection",
    "ReportingPeriod",
    # Language
    "LanguageCodeEnum",
    # Core
    "IconThumbnailFormatEnum",
    "JobStatusEnum",
    "TimePeriodTypeEnum",
    "ThumbnailFormatEnum",
    "AllocationStrategyEnum",
    "MarkAsPaidStrategyEnum",
    "TransactionFlowStrategyEnum",
    # Units
    "MeasurementUnitsEnum",
    "DistanceUnitsEnum",
    "AreaUnitsEnum",
    "VolumeUnitsEnum",
    "WeightUnitsEnum",
    "unit_enums",
    # Order
    "OrderStatusEnum",
    "OrderOriginEnum",
    "OrderAuthorizeStatusEnum",
    "OrderChargeStatusEnum",
    "OrderGrantedRefundStatusEnum",
    "FulfillmentStatusEnum",
    "OrderEventsEnum",
    "OrderEventsEmailsEnum",
    # Helper
    "to_enum",
]