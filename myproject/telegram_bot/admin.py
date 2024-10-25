from django.contrib import admin
from .models import Client, VPNConfig

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'subscription_start', 'subscription_end', 'assigned_config')
    search_fields = ('telegram_id',)

@admin.register(VPNConfig)
class VPNConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_assigned')
    list_filter = ('is_assigned',)
    search_fields = ('name', 'config_text')