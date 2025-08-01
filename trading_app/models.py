from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

# Choix pour les plateformes
BROKER_CHOICES = [
    ('saxo', 'Saxo Bank'),
    ('binance', 'Binance'),
    ('yahoo', 'Yahoo Finance'),
]

class AssetType(models.Model):
    """Types d'actifs (Action, ETF, Crypto, etc.)"""
    name = models.CharField(max_length=50, unique=True)
    platform_id = models.CharField(max_length=50, blank=True)  # ID spécifique à la plateforme
    
    def __str__(self):
        return self.name

class Market(models.Model):
    """Marchés (NASDAQ, NYSE, EURONEXT, etc.)"""
    name = models.CharField(max_length=50, unique=True)
    platform_id = models.CharField(max_length=50, blank=True)  # ID spécifique à la plateforme
    
    def __str__(self):
        return self.name

class Asset(models.Model):
    """Actif sous-jacent (peut avoir plusieurs versions tradables)"""
    symbol = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    sector = models.CharField(max_length=100, default='xxxx')
    industry = models.CharField(max_length=100, default='xxxx')
    market_cap = models.FloatField(default=0.0)
    price_history = models.TextField(default='xxxx')
    
    def __str__(self):
        return self.symbol

class AssetTradable(models.Model):
    """Actifs tradables sur une plateforme spécifique"""
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='tradable_versions')
    symbol = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    platform = models.CharField(max_length=20, choices=BROKER_CHOICES)
    asset_type = models.ForeignKey(AssetType, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['symbol', 'platform']  # Un symbole unique par plateforme
    
    def __str__(self):
        return f"{self.symbol} ({self.platform})"

class BrokerCredentials(models.Model):
    """Modèle pour stocker les credentials des courtiers"""
    BROKER_CHOICES = [
        ('saxo', 'Saxo Bank'),
        ('binance', 'Binance'),
    ]
    
    ENVIRONMENT_CHOICES = [
        ('live', 'Live Trading'),
        ('simulation', 'Simulation/Demo'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    broker_type = models.CharField(max_length=20, choices=BROKER_CHOICES)
    name = models.CharField(max_length=100, help_text="Nom pour identifier cette configuration")
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES, default='simulation', help_text="Environnement de trading (Live ou Simulation)")
    
    # Credentials Saxo
    saxo_client_id = models.CharField(max_length=100, blank=True, null=True)
    saxo_client_secret = models.CharField(max_length=100, blank=True, null=True)
    saxo_redirect_uri = models.URLField(blank=True, null=True)
    saxo_access_token = models.TextField(blank=True, null=True)
    saxo_refresh_token = models.TextField(blank=True, null=True)
    saxo_token_expires_at = models.DateTimeField(blank=True, null=True)
    
    # Credentials Binance
    binance_api_key = models.CharField(max_length=100, blank=True, null=True)
    binance_api_secret = models.CharField(max_length=100, blank=True, null=True)
    binance_testnet = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'broker_type', 'name']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_broker_type_display()} - {self.name}"
    
    def get_credentials_dict(self) -> dict:
        """Retourner les credentials sous forme de dictionnaire"""
        if self.broker_type == 'saxo':
            return {
                'client_id': self.saxo_client_id,
                'client_secret': self.saxo_client_secret,
                'redirect_uri': self.saxo_redirect_uri,
                'access_token': self.saxo_access_token,
                'refresh_token': self.saxo_refresh_token,
                'token_expires_at': self.saxo_token_expires_at,
                'environment': self.environment,
            }
        elif self.broker_type == 'binance':
            return {
                'api_key': self.binance_api_key,
                'api_secret': self.binance_api_secret,
                'testnet': self.binance_testnet,
                'environment': self.environment,
            }
        return {}

class Strategy(models.Model):
    """Modèle pour les stratégies de trading"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Position(models.Model):
    """Modèle pour les positions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset_tradable = models.ForeignKey(AssetTradable, on_delete=models.CASCADE)
    size = models.DecimalField(max_digits=15, decimal_places=2)
    entry_price = models.DecimalField(max_digits=15, decimal_places=5)
    current_price = models.DecimalField(max_digits=15, decimal_places=5)
    side = models.CharField(max_length=4)  # BUY, SELL
    status = models.CharField(max_length=10)  # OPEN, CLOSED
    pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def calculate_pnl(self):
        """Calcule le P&L de la position"""
        if self.side == 'BUY':
            return (self.current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - self.current_price) * self.size

class Trade(models.Model):
    """Modèle pour les trades"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset_tradable = models.ForeignKey(AssetTradable, on_delete=models.CASCADE)
    size = models.DecimalField(max_digits=15, decimal_places=2)
    price = models.DecimalField(max_digits=15, decimal_places=5)
    side = models.CharField(max_length=4)  # BUY, SELL
    timestamp = models.DateTimeField(auto_now_add=True)
    platform = models.CharField(max_length=20)
    
    def __str__(self):
        return f"{self.side} {self.size} {self.asset_tradable.symbol} @ {self.price}"

class AllAssets(models.Model):
    """Catalogue universel d'actifs récupérés depuis les APIs des brokers"""
    symbol = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    platform = models.CharField(max_length=20, choices=BROKER_CHOICES)
    asset_type = models.CharField(max_length=50)  # Stock, Crypto, ETF, Bond, etc.
    market = models.CharField(max_length=50)  # NYSE, NASDAQ, SPOT, FUTURES, etc.
    currency = models.CharField(max_length=10, default='USD')
    exchange = models.CharField(max_length=100, blank=True)
    is_tradable = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Champs spécifiques Saxo
    saxo_uic = models.IntegerField(null=True, blank=True)
    saxo_exchange_id = models.CharField(max_length=20, blank=True)
    saxo_country_code = models.CharField(max_length=10, blank=True)
    
    # Champs spécifiques Binance
    binance_base_asset = models.CharField(max_length=20, blank=True)
    binance_quote_asset = models.CharField(max_length=20, blank=True)
    binance_status = models.CharField(max_length=20, blank=True)
    
    class Meta:
        unique_together = ['symbol', 'platform']
        indexes = [
            models.Index(fields=['platform', 'asset_type']),
            models.Index(fields=['symbol']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.symbol} ({self.platform}) - {self.name}"
    
    @property
    def display_name(self):
        """Nom d'affichage pour l'autocomplétion"""
        return f"{self.symbol} - {self.name}"
