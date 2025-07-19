from django.contrib import admin
from .models import Asset, Position, Trade, Strategy

admin.site.register(Asset)
admin.site.register(Position)
admin.site.register(Trade)
admin.site.register(Strategy)
