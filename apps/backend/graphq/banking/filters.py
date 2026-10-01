import django_filters
from graphq.common.filter_overrides import FILTER_OVERRIDES
from banking.models import Bank
class BankFilterSet(django_filters.FilterSet):
    class Meta:
        model = Bank
        fields = {
            "name": ["exact", "icontains"],
            "code": ["exact"],
            "is_active": ["exact"],
        }
        filter_overrides = FILTER_OVERRIDES