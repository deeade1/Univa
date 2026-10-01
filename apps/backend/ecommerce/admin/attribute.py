from django.contrib import admin

from ecommerce.models.attribute import (AssignedProductAttributeValue,
                              AssignedVariantAttribute,
                              AssignedVariantAttributeValue, Attribute,
                              AttributeProduct, AttributeValue,
                              AttributeVariant)


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'input_type')
    search_fields = ('name', 'slug')
    list_filter = ('input_type',)
    ordering = ('name',)


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'attribute')
    search_fields = ('name', 'slug', 'attribute__name')
    list_filter = ('attribute',)
    ordering = ('name',)



@admin.register(AttributeProduct)
class AttributeProductAdmin(admin.ModelAdmin):
    list_display = ('attribute', 'product_type')
    search_fields = ('attribute__name',)
    list_filter = ('product_type',)


@admin.register(AssignedProductAttributeValue)
class AssignedProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ('product', 'value')
    search_fields = ('product__attribute__name', 'value__name')
    

@admin.register(AssignedVariantAttribute)
class AssignedVariantAttributeAdmin(admin.ModelAdmin):
    list_display = ('variant', 'assignment')  # Removed space before assignment
    search_fields = ('variant__name', 'assignment__attribute__name')

@admin.register(AssignedVariantAttributeValue)
class AssignedVariantAttributeValueAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'value')  # Changed from variant to assignment
    search_fields = ('assignment__attribute__name', 'value__name')

@admin.register(AttributeVariant)
class AttributeVariantAdmin(admin.ModelAdmin):
    list_display = ('attribute', 'product_type')  # Changed from variant_type to product_type
    search_fields = ('attribute__name',)
    list_filter = ('product_type',)  # Changed from variant_type to product_type