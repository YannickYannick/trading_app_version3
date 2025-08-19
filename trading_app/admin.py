from django.contrib import admin
from .models import AssetType, Market, AssetTradable, Asset, Position, Trade, Strategy, BrokerCredentials, AllAssets, PendingOrder, TokenRefreshHistory, AutomationConfig, AutomationExecutionLog

admin.site.register(AssetType)
admin.site.register(Market)
admin.site.register(AssetTradable)
admin.site.register(Asset)
admin.site.register(Position)
admin.site.register(Trade)
admin.site.register(Strategy)
admin.site.register(PendingOrder)

@admin.register(AllAssets)
class AllAssetsAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'platform', 'asset_type', 'market', 'currency', 'is_tradable', 'last_updated']
    list_filter = ['platform', 'asset_type', 'market', 'currency', 'is_tradable']
    search_fields = ['symbol', 'name']
    readonly_fields = ['last_updated', 'created_at']
    ordering = ['platform', 'symbol']

@admin.register(TokenRefreshHistory)
class TokenRefreshHistoryAdmin(admin.ModelAdmin):
    """Admin pour l'historique des refresh de tokens"""
    list_display = ['broker_credentials', 'refresh_attempted_at', 'success', 'retry_count', 'max_retries']
    list_filter = ['success', 'broker_credentials__broker_type', 'refresh_attempted_at']
    search_fields = ['broker_credentials__name', 'error_message']
    readonly_fields = ['refresh_attempted_at']
    ordering = ['-refresh_attempted_at']
    
    def get_queryset(self, request):
        """Filtrer automatiquement les entrées de plus de 30 jours"""
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=30)
        return super().get_queryset(request).filter(refresh_attempted_at__gte=cutoff_date)

@admin.register(BrokerCredentials)
class BrokerCredentialsAdmin(admin.ModelAdmin):
    """Admin pour les credentials des brokers"""
    list_display = ['name', 'user', 'broker_type', 'auto_refresh_enabled', 'auto_refresh_frequency', 'created_at']
    list_filter = ['broker_type', 'auto_refresh_enabled', 'created_at']
    search_fields = ['name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('user', 'name', 'broker_type')
        }),
        ('Configuration Saxo Bank', {
            'fields': ('saxo_client_id', 'saxo_client_secret', 'saxo_redirect_uri', 'saxo_environment'),
            'classes': ('collapse',),
            'description': 'Configuration OAuth2 pour Saxo Bank'
        }),
        ('Tokens Saxo Bank', {
            'fields': ('saxo_access_token', 'saxo_refresh_token', 'saxo_token_expires_at'),
            'classes': ('collapse',),
            'description': 'Tokens d\'authentification Saxo Bank'
        }),
        ('Configuration Auto-Refresh', {
            'fields': ('auto_refresh_enabled', 'auto_refresh_frequency'),
            'description': 'Configuration du refresh automatique des tokens'
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(AutomationConfig)
class AutomationConfigAdmin(admin.ModelAdmin):
    """Admin pour la configuration de l'automatisation"""
    list_display = ['user', 'is_active', 'frequency_minutes', 'last_execution', 'next_execution', 'created_at']
    list_filter = ['is_active', 'frequency_minutes', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['last_execution', 'next_execution', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Configuration', {
            'fields': ('user', 'is_active', 'frequency_minutes')
        }),
        ('Exécution', {
            'fields': ('last_execution', 'next_execution'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(AutomationExecutionLog)
class AutomationExecutionLogAdmin(admin.ModelAdmin):
    """Admin pour l'historique des exécutions d'automatisation"""
    list_display = ['user', 'execution_time', 'status', 'execution_duration']
    list_filter = ['status', 'user', 'execution_time']
    search_fields = ['user__username', 'summary', 'errors']
    readonly_fields = ['execution_time']
    ordering = ['-execution_time']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('user', 'execution_time', 'status', 'execution_duration')
        }),
        ('Résultats', {
            'fields': ('summary', 'api_responses', 'errors'),
            'classes': ('collapse',)
        })
    )
