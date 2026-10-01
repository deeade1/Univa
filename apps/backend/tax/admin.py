from django.contrib import admin
from django.contrib.admin.widgets import AdminTextInputWidget
from django.db import models
from django.forms import TextInput
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_admin_listfilter_dropdown.filters import (ChoiceDropdownFilter,
                                                      RelatedDropdownFilter)

from .models import (TaxClass, TaxClassCountryRate, TaxConfiguration,
                     TaxConfigurationPerCountry)


class TaxClassCountryRateInline(admin.TabularInline):
    model = TaxClassCountryRate
    extra = 1
    min_num = 1
    formfield_overrides = {
        models.DecimalField: {'widget': TextInput(attrs={'size': '10'})},
    }
    fields = ('country', 'rate', 'is_default')
    readonly_fields = ('is_default',)

    def is_default(self, obj):
        return obj.tax_class is None
    is_default.boolean = True
    is_default.short_description = _("Default Rate")


@admin.register(TaxClass)
class TaxClassAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'country_rates_count',
    )
    search_fields = ('name',)
    inlines = (TaxClassCountryRateInline,)
    readonly_fields = ('country_rates_count',)
    formfield_overrides = {
        models.CharField: {'widget': AdminTextInputWidget(attrs={'size': '50'})},
    }
    save_on_top = True
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('country_rates')

    def country_rates_count(self, obj):
        url = (
            reverse("admin:tax_taxclasscountryrate_changelist")
            + f"?tax_class__id__exact={obj.id}"
        )
        return format_html('<a href="{}">{}</a>', url, obj.country_rates.count())
    country_rates_count.short_description = _("Country Rates")

    fieldsets = (
        (None, {
            'fields': ('name', 'metadata')
        }),
        (_("Statistics"), {
            'fields': ('country_rates_count',),
            'classes': ('collapse',)
        }),
    )


class TaxClassFilter(admin.SimpleListFilter):
    title = _('tax class')
    parameter_name = 'tax_class'

    def lookups(self, request, model_admin):
        return (
            ('default', _('Default Rates')),
            ('custom', _('Custom Rates')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'default':
            return queryset.filter(tax_class__isnull=True)
        if self.value() == 'custom':
            return queryset.filter(tax_class__isnull=False)


@admin.register(TaxClassCountryRate)
class TaxClassCountryRateAdmin(admin.ModelAdmin):
    list_display = (
        'country',
        'rate_display',
        'tax_class_link',
        'is_default',
    )
    list_filter = (
        TaxClassFilter,
        ('tax_class', RelatedDropdownFilter),
    )
    search_fields = (
        'country',
        'tax_class__name',
    )
    readonly_fields = ('is_default',)
    list_select_related = ('tax_class',)
    actions = ['convert_to_default_rates', 'convert_to_custom_rates']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tax_class')

    def rate_display(self, obj):
        return f"{obj.rate}%"
    rate_display.short_description = _("Rate")
    rate_display.admin_order_field = "rate"

    def tax_class_link(self, obj):
        if not obj.tax_class:
            return _("Default Rate")
        url = reverse("admin:tax_taxclass_change", args=[obj.tax_class.id])
        return format_html('<a href="{}">{}</a>', url, obj.tax_class)
    tax_class_link.short_description = _("Tax Class")
    tax_class_link.admin_order_field = "tax_class__name"

    def is_default(self, obj):
        return obj.tax_class is None
    is_default.boolean = True
    is_default.short_description = _("Default Rate")

    @admin.action(description=_("Convert selected to default rates"))
    def convert_to_default_rates(self, request, queryset):
        updated = queryset.update(tax_class=None)
        self.message_user(request, _("%d rates converted to default rates.") % updated)

    @admin.action(description=_("Convert selected to custom rates"))
    def convert_to_custom_rates(self, request, queryset):
        from django import forms
        class TaxClassForm(forms.Form):
            tax_class = forms.ModelChoiceField(queryset=TaxClass.objects.all())

        if 'apply' in request.POST:
            form = TaxClassForm(request.POST)
            if form.is_valid():
                tax_class = form.cleaned_data['tax_class']
                updated = queryset.update(tax_class=tax_class)
                self.message_user(request, _("%d rates converted to custom rates.") % updated)
                return
        else:
            form = TaxClassForm()

        return admin.site.admin_view(self.convert_to_custom_rates_intermediate)(
            request, queryset, form
        )

    def convert_to_custom_rates_intermediate(self, request, queryset, form):
        return render(
            request,
            'admin/tax/convert_to_custom_rates.html',
            context={
                'title': _("Select Tax Class"),
                'queryset': queryset,
                'form': form,
                'action': 'convert_to_custom_rates',
                'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
            },
        )

    fieldsets = (
        (None, {
            'fields': ('country', 'rate', 'tax_class')
        }),
        (_("Status"), {
            'fields': ('is_default',),
            'classes': ('collapse',)
        }),
    )


class TaxConfigurationPerCountryInline(admin.TabularInline):
    model = TaxConfigurationPerCountry
    extra = 1
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '20'})},
    }
    fields = (
        'country',
        'charge_taxes',
        'tax_calculation_strategy',
        'display_gross_prices',
        'tax_app_id',
    )


@admin.register(TaxConfiguration)
class TaxConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        'channel_link',
        'charge_taxes',
        'tax_calculation_strategy_display',
        'display_gross_prices',
        'prices_entered_with_tax',
        'country_exceptions_count',
    )
    list_filter = (
        'charge_taxes',
        'tax_calculation_strategy',
        'display_gross_prices',
        'prices_entered_with_tax',
        ('channel', RelatedDropdownFilter),
    )
    search_fields = (
        'channel__name',
        'tax_app_id',
    )
    readonly_fields = ('country_exceptions_count',)
    inlines = (TaxConfigurationPerCountryInline,)
    list_select_related = ('channel',)
    actions = ['enable_tax_charging', 'disable_tax_charging']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('channel').prefetch_related('country_exceptions')

    def channel_link(self, obj):
        url = reverse("admin:channel_channel_change", args=[obj.channel.id])
        return format_html('<a href="{}">{}</a>', url, obj.channel)
    channel_link.short_description = _("Channel")
    channel_link.admin_order_field = "channel__name"

    def tax_calculation_strategy_display(self, obj):
        return obj.get_tax_calculation_strategy_display() if obj.tax_calculation_strategy else "-"
    tax_calculation_strategy_display.short_description = _("Calculation Strategy")
    tax_calculation_strategy_display.admin_order_field = "tax_calculation_strategy"

    def country_exceptions_count(self, obj):
        url = (
            reverse("admin:tax_taxconfigurationpercountry_changelist")
            + f"?tax_configuration__id__exact={obj.id}"
        )
        return format_html('<a href="{}">{}</a>', url, obj.country_exceptions.count())
    country_exceptions_count.short_description = _("Country Exceptions")

    @admin.action(description=_("Enable tax charging for selected"))
    def enable_tax_charging(self, request, queryset):
        updated = queryset.update(charge_taxes=True)
        self.message_user(request, _("%d configurations updated to charge taxes.") % updated)

    @admin.action(description=_("Disable tax charging for selected"))
    def disable_tax_charging(self, request, queryset):
        updated = queryset.update(charge_taxes=False)
        self.message_user(request, _("%d configurations updated to not charge taxes.") % updated)

    fieldsets = (
        (None, {
            'fields': (
                'channel',
                'charge_taxes',
                'tax_calculation_strategy',
                'display_gross_prices',
                'prices_entered_with_tax',
                'tax_app_id',
                'metadata',
            )
        }),
        (_("Statistics"), {
            'fields': ('country_exceptions_count',),
            'classes': ('collapse',)
        }),
    )


@admin.register(TaxConfigurationPerCountry)
class TaxConfigurationPerCountryAdmin(admin.ModelAdmin):
    list_display = (
        'tax_configuration_link',
        'country',
        'charge_taxes',
        'tax_calculation_strategy_display',
        'display_gross_prices',
    )
    list_filter = (
        'charge_taxes',
        'display_gross_prices',
        ('tax_configuration__channel', RelatedDropdownFilter),
        ('country', ChoiceDropdownFilter),
        ('tax_calculation_strategy', ChoiceDropdownFilter),
    )
    search_fields = (
        'country',
        'tax_configuration__channel__name',
        'tax_app_id',
    )
    list_select_related = ('tax_configuration__channel',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tax_configuration__channel')

    def tax_configuration_link(self, obj):
        url = reverse("admin:tax_taxconfiguration_change", args=[obj.tax_configuration.id])
        return format_html('<a href="{}">{}</a>', url, obj.tax_configuration.channel)
    tax_configuration_link.short_description = _("Channel Configuration")
    tax_configuration_link.admin_order_field = "tax_configuration__channel__name"

    def tax_calculation_strategy_display(self, obj):
        return obj.get_tax_calculation_strategy_display() if obj.tax_calculation_strategy else "-"
    tax_calculation_strategy_display.short_description = _("Calculation Strategy")
    tax_calculation_strategy_display.admin_order_field = "tax_calculation_strategy"

    fieldsets = (
        (None, {
            'fields': (
                'tax_configuration',
                'country',
                'charge_taxes',
                'tax_calculation_strategy',
                'display_gross_prices',
                'tax_app_id',
            )
        }),
    )