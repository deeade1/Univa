import graphene
from django.conf import settings

from ecommerce.models.constants import (AllocationStrategy, MarkAsPaidStrategy,
                     TransactionFlowStrategy)
from core import JobStatus, TimePeriodType
from core.units import (AreaUnits, DistanceUnits, MeasurementUnits,
                        VolumeUnits, WeightUnits)
from thumbnail import IconThumbnailFormat, ThumbnailFormat

from .utils import str_to_enum


class OrderDirection(graphene.Enum):
    ASC = ""
    DESC = "-"

    @property
    def description(self):
        # Disable all the no-member violations in this function
        # pylint: disable=no-member
        if self == OrderDirection.ASC:
            return "Specifies an ascending sort order."
        if self == OrderDirection.DESC:
            return "Specifies a descending sort order."
        raise ValueError(f"Unsupported enum value: {self.value}")


class ReportingPeriod(graphene.Enum):
    TODAY = "TODAY"
    THIS_MONTH = "THIS_MONTH"


def to_enum(enum_cls, *, type_name=None, **options) -> graphene.Enum:
    """Create a Graphene enum from a class containing a set of options.

    :param enum_cls:
        The class to build the enum from.
    :param type_name:
        The name of the type. Default is the class name + 'Enum'.
    :param options:
        - description:
            Contains the type description (default is the class's docstring)
        - deprecation_reason:
            Contains the deprecation reason.
            The default is enum_cls.__deprecation_reason__ or None.
    :return:
    """

  
    deprecation_reason = getattr(enum_cls, "__deprecation_reason__", None)
    if deprecation_reason:
        options.setdefault("deprecation_reason", deprecation_reason)

    type_name = type_name or (enum_cls.__name__ + "Enum")
    enum_data = [(str_to_enum(code.upper()), code) for code, name in enum_cls.CHOICES]
    return graphene.Enum(type_name, enum_data, **options)


LanguageCodeEnum = graphene.Enum(
    "LanguageCodeEnum",
    [(lang[0].replace("-", "_").upper(), lang[0]) for lang in settings.LANGUAGES],
)

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


# unit enums
MeasurementUnitsEnum = to_enum(MeasurementUnits)
DistanceUnitsEnum = to_enum(DistanceUnits)
AreaUnitsEnum = to_enum(AreaUnits)
VolumeUnitsEnum = to_enum(VolumeUnits)
WeightUnitsEnum = to_enum(WeightUnits)
unit_enums = [DistanceUnitsEnum, AreaUnitsEnum, VolumeUnitsEnum, WeightUnitsEnum]
