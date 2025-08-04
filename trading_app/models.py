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
    

    
    def save(self, *args, **kwargs):
        """Override save pour mettre le symbole en majuscules"""
        if self.symbol:
            self.symbol = self.symbol.upper()
        super().save(*args, **kwargs)
    
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
    
    def get_clean_symbol(self):
        """Retourne le symbole sans extensions"""
        if not self.symbol:
            return ""
        # Enlever les extensions :XNAS, _0, _1, etc.
        clean = self.symbol.split(':')[0]  # Enlever :XNAS
        clean = clean.split('_')[0]        # Enlever _0, _1, etc.
        return clean.upper()

class Asset(models.Model):
    """Actif sous-jacent avec données enrichies (secteur, industrie, market cap, historique)"""
    # Référence optionnelle vers AllAssets
    all_asset = models.ForeignKey(AllAssets, on_delete=models.SET_NULL, null=True, blank=True, related_name='enriched_assets')
    
    # Symbole original (peut contenir des extensions)
    symbol = models.CharField(max_length=20, unique=True)
    
    # Symbole nettoyé (sans extensions, pour affichage)
    symbol_clean = models.CharField(max_length=20, blank=True)
    
    name = models.CharField(max_length=100)
    sector = models.CharField(max_length=100, default='xxxx')
    industry = models.CharField(max_length=100, default='xxxx')
    market_cap = models.FloatField(default=0.0)
    price_history = models.TextField(default='xxxx')
    
    def __str__(self):
        return self.symbol_clean or self.symbol
    
    def save(self, *args, **kwargs):
        """Override save pour générer automatiquement symbol_clean"""
        if self.symbol and not self.symbol_clean:
            self.symbol_clean = self.get_clean_symbol()
        super().save(*args, **kwargs)
    
    def get_clean_symbol(self):
        """Retourne le symbole sans extensions"""
        if not self.symbol:
            return ""
        # Enlever les extensions :XNAS, _0, _1, etc.
        clean = self.symbol.split(':')[0]  # Enlever :XNAS
        clean = clean.split('_')[0]        # Enlever _0, _1, etc.
        return clean.upper()
    
    @classmethod
    def find_by_all_asset_symbol(cls, symbol):
        """Trouve un Asset basé sur un symbole AllAssets"""
        clean_symbol = symbol.split(':')[0].split('_')[0].upper()
        return cls.objects.filter(symbol_clean=clean_symbol).first()

class AssetTradable(models.Model):
    """Actifs tradables sur une plateforme spécifique"""
    # Référence obligatoire vers AllAssets
    all_asset = models.ForeignKey(AllAssets, on_delete=models.CASCADE, related_name='tradable_versions')
    
    # Données copiées depuis AllAssets (pour garder l'AssetTradable même si AllAssets est supprimé)
    symbol = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    platform = models.CharField(max_length=20, choices=BROKER_CHOICES)
    asset_type = models.ForeignKey(AssetType, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    
    # Champs additionnels spécifiques à l'AssetTradable
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['symbol', 'platform']  # Un symbole unique par plateforme
    
    def __str__(self):
        return f"{self.symbol} ({self.platform})"
    
    def save(self, *args, **kwargs):
        """Override save pour mettre le symbole en majuscules"""
        if self.symbol:
            self.symbol = self.symbol.upper()
        super().save(*args, **kwargs)
    
    def copy_from_all_asset(self, all_asset):
        """Copie les données depuis un AllAssets"""
        self.all_asset = all_asset
        self.symbol = all_asset.symbol.upper()  # Forcer en majuscules
        self.name = all_asset.name
        self.platform = all_asset.platform
        
        # Créer ou récupérer AssetType et Market
        asset_type, _ = AssetType.objects.get_or_create(name=all_asset.asset_type)
        market, _ = Market.objects.get_or_create(name=all_asset.market)
        
        self.asset_type = asset_type
        self.market = market
        self.save()
    
    @classmethod
    def find_matching_all_asset(cls, symbol, platform):
        """Trouve un AllAssets correspondant en ignorant la casse et les extensions"""
        # Nettoyer le symbole : enlever les extensions (_0, _1, etc.) et mettre en majuscules
        base_symbol = symbol.upper().split('_')[0]
        
        # Chercher dans AllAssets avec différentes variations
        all_assets = AllAssets.objects.filter(
            platform=platform
        )
        
        for all_asset in all_assets:
            # Comparer les symboles de base (sans extensions)
            all_asset_base = all_asset.symbol.upper().split('_')[0]
            
            # Correspondance exacte
            if all_asset_base == base_symbol:
                return all_asset
            
            # Pour Binance : gérer les différents formats de symboles
            if platform == 'binance':
                # Essayer de matcher BTC avec BTCUSDT, BTC/USDT, etc.
                if all_asset_base.startswith(base_symbol) and len(all_asset_base) > len(base_symbol):
                    # Vérifier si c'est un format de paire (BTCUSDT, BTC/USDT, etc.)
                    remaining = all_asset_base[len(base_symbol):]
                    if remaining in ['USDT', 'USD', 'BTC', 'ETH', 'BNB', 'BUSD', '/USDT', '/USD', '/BTC', '/ETH', '/BNB', '/BUSD']:
                        return all_asset
                
                # Essayer de matcher BTCUSDT avec BTC
                if base_symbol.startswith(all_asset_base) and len(base_symbol) > len(all_asset_base):
                    remaining = base_symbol[len(all_asset_base):]
                    if remaining in ['USDT', 'USD', 'BTC', 'ETH', 'BNB', 'BUSD']:
                        return all_asset
        
        return None

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
    """Modèle pour les stratégies de trading automatisées"""
    
    # Types d'algorithmes disponibles
    ALGORITHM_CHOICES = [
        ('threshold', 'Seuils (Threshold)'),
        ('ma_crossover', 'Moving Average Crossover'),
        ('rsi', 'RSI (Relative Strength Index)'),
        ('bollinger', 'Bollinger Bands'),
        ('macd', 'MACD'),
        ('grid', 'Grid Trading'),
    ]
    
    # Modes d'exécution
    EXECUTION_MODE_CHOICES = [
        ('simulation', 'Simulation'),
        ('paper_trading', 'Paper Trading'),
        ('live_trading', 'Trading Réel'),
    ]
    
    # Statuts
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('paused', 'En Pause'),
    ]
    
    # Informations de base
    name = models.CharField(max_length=100, help_text="Nom de la stratégie")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, help_text="Asset sur lequel appliquer la stratégie")
    algorithm_type = models.CharField(max_length=20, choices=ALGORITHM_CHOICES, default='threshold', help_text="Type d'algorithme")
    
    # Paramètres de l'algorithme (JSON)
    parameters = models.JSONField(default=dict, help_text="Paramètres spécifiques à l'algorithme")
    
    # Configuration d'exécution
    broker = models.ForeignKey(BrokerCredentials, on_delete=models.CASCADE, help_text="Broker pour exécuter les ordres")
    execution_mode = models.CharField(max_length=20, choices=EXECUTION_MODE_CHOICES, default='simulation')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inactive')
    
    # Fréquence de vérification (en minutes)
    check_frequency = models.IntegerField(default=45, help_text="Fréquence de vérification en minutes")
    
    # Commentaires
    comments = models.TextField(blank=True, help_text="Commentaires sur la stratégie")
    
    # Métadonnées
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_execution = models.DateTimeField(null=True, blank=True)
    
    # Statistiques
    total_trades = models.IntegerField(default=0)
    successful_trades = models.IntegerField(default=0)
    total_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['user', 'asset', 'name']  # Un nom unique par utilisateur et asset
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['algorithm_type']),
            models.Index(fields=['asset']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.asset.symbol_clean or self.asset.symbol}) - {self.get_algorithm_type_display()}"
    
    def get_algorithm_instance(self):
        """Retourne une instance de l'algorithme correspondant"""
        from .algorithms import AlgorithmFactory
        return AlgorithmFactory.create_algorithm(self.algorithm_type, self.parameters)
    
    def calculate_signals(self, price_data):
        """Calcule les signaux d'achat/vente basés sur l'algorithme"""
        algorithm = self.get_algorithm_instance()
        return algorithm.calculate_signals(price_data)
    
    def should_execute_order(self, signal):
        """Détermine si un ordre doit être exécuté selon le mode"""
        if self.execution_mode == 'simulation':
            return False  # Pas d'exécution en simulation
        elif self.execution_mode == 'paper_trading':
            return True   # Exécution en paper trading
        elif self.execution_mode == 'live_trading':
            return True   # Exécution en trading réel
        return False
    
    def get_parameter_display(self):
        """Retourne une représentation lisible des paramètres"""
        if self.algorithm_type == 'threshold':
            return f"Seuil bas: {self.parameters.get('threshold_low', 'N/A')}, Seuil haut: {self.parameters.get('threshold_high', 'N/A')}"
        elif self.algorithm_type == 'ma_crossover':
            return f"MA1: {self.parameters.get('ma1_period', 'N/A')}, MA2: {self.parameters.get('ma2_period', 'N/A')}"
        elif self.algorithm_type == 'rsi':
            return f"Période: {self.parameters.get('rsi_period', 'N/A')}, Seuils: {self.parameters.get('rsi_low', 'N/A')}-{self.parameters.get('rsi_high', 'N/A')}"
        elif self.algorithm_type == 'bollinger':
            return f"Période: {self.parameters.get('bb_period', 'N/A')}, Écart-type: {self.parameters.get('bb_std', 'N/A')}"
        elif self.algorithm_type == 'macd':
            return f"Rapide: {self.parameters.get('macd_fast', 'N/A')}, Lent: {self.parameters.get('macd_slow', 'N/A')}, Signal: {self.parameters.get('macd_signal', 'N/A')}"
        elif self.algorithm_type == 'grid':
            return f"Min: {self.parameters.get('grid_min', 'N/A')}, Max: {self.parameters.get('grid_max', 'N/A')}, Niveaux: {self.parameters.get('grid_levels', 'N/A')}"
        return "Paramètres non disponibles"

class StrategyExecution(models.Model):
    """Historique des exécutions de stratégies"""
    
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='executions')
    
    # Données de l'exécution
    execution_time = models.DateTimeField(auto_now_add=True)
    current_price = models.DecimalField(max_digits=15, decimal_places=5)
    signal = models.CharField(max_length=10)  # 'BUY', 'SELL', 'HOLD'
    signal_strength = models.FloatField(default=0.0)  # Force du signal (0-1)
    
    # Résultat de l'exécution
    order_executed = models.BooleanField(default=False)
    order_size = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    order_price = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    
    # Métadonnées
    execution_duration = models.FloatField(default=0.0)  # Durée en secondes
    error_message = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['strategy', 'execution_time']),
            models.Index(fields=['signal']),
        ]
    
    def __str__(self):
        return f"{self.strategy.name} - {self.execution_time} - {self.signal}"

class Position(models.Model):
    """Modèle pour les positions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
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
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    size = models.DecimalField(max_digits=15, decimal_places=2)
    price = models.DecimalField(max_digits=15, decimal_places=5)
    side = models.CharField(max_length=4)  # BUY, SELL
    timestamp = models.DateTimeField(auto_now_add=True)
    platform = models.CharField(max_length=20)
    
    def __str__(self):
        return f"{self.side} {self.size} {self.asset.symbol_clean} @ {self.price}"

