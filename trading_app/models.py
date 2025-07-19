from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Asset(models.Model):
    """Modèle pour les actifs"""
    symbol = models.CharField(max_length=20, unique=True, default='xxxx')
    name = models.CharField(max_length=100, default='xxxx')
    type = models.CharField(max_length=20, default='xxxx')  # FOREX, STOCK, CRYPTO
    platform = models.CharField(max_length=20, default='xxxx')  # XTB, BINANCE, DEGIRO
    last_price = models.FloatField(default=0.0)  # type: ignore
    is_active = models.BooleanField(default=True)  # type: ignore
    
    sector = models.CharField(max_length=100, default='xxxx')
    industry = models.CharField(max_length=100, default='xxxx')   
    market_cap = models.FloatField(default=0.0)  # type: ignore
    price_history = models.TextField(default='xxxx')

    data_source = models.TextField(default='yahoo')
    id_from_platform = models.CharField(max_length=100, default='xxxx')
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def save_from_dict(cls, asset_dict):
        asset = cls(
            symbol=asset_dict.get("symbol", "xxxx"),
            name=asset_dict.get("name", asset_dict.get("symbol", "xxxx")),
            type=asset_dict.get("type", "xxxx"),
            platform=asset_dict.get("platform", "xxxx"),
            last_price=asset_dict.get("last_price", asset_dict.get("price", 0)),
            is_active=asset_dict.get("is_active", True),
            sector=asset_dict.get("sector", "xxxx"),
            industry=asset_dict.get("industry", "xxxx"),
            market_cap=asset_dict.get("market_cap", asset_dict.get("cap", 0)),
            price_history=asset_dict.get("price_history", asset_dict.get("history", "xxxx")),
            data_source=asset_dict.get("data_source", asset_dict.get("source", "yahoo")),
            id_from_platform=asset_dict.get("id_from_platform", asset_dict.get("ID", "xxxx")),)
        asset.save()
        return asset

    def __str__(self):
        return f"{self.symbol} ({self.platform})"

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
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    strategy = models.ForeignKey(Strategy, on_delete=models.SET_NULL, null=True, blank=True)
    size = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    entry_price = models.DecimalField(max_digits=15, decimal_places=5, default=0)
    current_price = models.DecimalField(max_digits=15, decimal_places=5, default=0)
    side = models.CharField(max_length=4)  # BUY, SELL
    status = models.CharField(max_length=10)  # OPEN, CLOSED
    pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def calculate_pnl(self):
        """Calcule le P&L de la position"""
        entry = Decimal(str(self.entry_price or 0))
        current = Decimal(str(self.current_price or 0))
        size = Decimal(str(self.size or 0))
        if self.side == 'BUY':
            return (current - entry) * size
        else:
            return (entry - current) * size

class Trade(models.Model):
    """Modèle pour les trades"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    strategy = models.ForeignKey(Strategy, on_delete=models.SET_NULL, null=True, blank=True)
    size = models.DecimalField(max_digits=15, decimal_places=2)
    price = models.DecimalField(max_digits=15, decimal_places=5)
    side = models.CharField(max_length=4)  # BUY, SELL
    timestamp = models.DateTimeField(auto_now_add=True)
    platform = models.CharField(max_length=20)
    
    def __str__(self):
        return f"{self.side} {self.size} {self.asset.symbol} @ {self.price}"
