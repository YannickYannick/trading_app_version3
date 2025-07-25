from django.contrib import admin
from .models import Asset, Position, Trade, Strategy, BrokerCredentials

admin.site.register(Asset)
admin.site.register(Position)
admin.site.register(Trade)
admin.site.register(Strategy)
admin.site.register(BrokerCredentials)
