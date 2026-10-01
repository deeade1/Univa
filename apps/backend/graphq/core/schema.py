'''import graphene
from django.conf import settings

from graphq.core.types.common import TaxType
from plugins.manager import PluginsManager


class CoreQueries(graphene.ObjectType):
    tax_types = graphene.List(graphene.NonNull(TaxType))

    def resolve_tax_types(self, info):
        plugins_manager = PluginsManager(settings.PLUGINS)
        tax_choices = plugins_manager.get_tax_rate_type_choices()
        return [
            TaxType(description=tax.description, tax_code=tax.code)
            for tax in tax_choices
        ]'''