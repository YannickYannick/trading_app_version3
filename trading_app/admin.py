from django.contrib import admin
from .models import AssetType, Market, AssetTradable, Asset, Position, Trade, Strategy, BrokerCredentials

admin.site.register(AssetType)
admin.site.register(Market)
admin.site.register(AssetTradable)
admin.site.register(Asset)
admin.site.register(Position)
admin.site.register(Trade)
admin.site.register(Strategy)
admin.site.register(BrokerCredentials)
