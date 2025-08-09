from django.contrib import admin
from .models import AssetType, Market, AssetTradable, Asset, Position, Trade, Strategy, BrokerCredentials, AllAssets, PendingOrder

admin.site.register(AssetType)
admin.site.register(Market)
admin.site.register(AssetTradable)
admin.site.register(Asset)
admin.site.register(Position)
admin.site.register(Trade)
admin.site.register(Strategy)
admin.site.register(BrokerCredentials)
admin.site.register(PendingOrder)

@admin.register(AllAssets)
class AllAssetsAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'platform', 'asset_type', 'market', 'currency', 'is_tradable', 'last_updated']
    list_filter = ['platform', 'asset_type', 'market', 'currency', 'is_tradable']
    search_fields = ['symbol', 'name']
    readonly_fields = ['last_updated', 'created_at']
    ordering = ['platform', 'symbol']
