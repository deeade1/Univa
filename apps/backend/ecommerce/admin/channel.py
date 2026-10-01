from django.contrib import admin

from ecommerce.models.channel import Channel


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    model = Channel
