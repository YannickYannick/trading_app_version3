"""
Services pour gérer les interactions avec les courtiers
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.contrib.auth.models import User
from .brokers.factory import BrokerFactory
from .models import BrokerCredentials, Asset, Trade, Position, AssetTradable, AssetType, Market


class BrokerService:
    """Service pour gérer les interactions avec les courtiers"""
    
    def __init__(self, user: User):
        self.user = user
    
    def get_user_brokers(self) -> List[BrokerCredentials]:
        """Récupérer tous les courtiers configurés pour l'utilisateur"""
        return BrokerCredentials.objects.filter(user=self.user, is_active=True)
    
    def get_broker_instance(self, broker_credentials: BrokerCredentials):
        """Créer une instance de courtier à partir des credentials"""
        credentials_dict = broker_credentials.get_credentials_dict()
        return BrokerFactory.create_broker(
            broker_credentials.broker_type,
            self.user,
            credentials_dict
        )
    
    def sync_positions_from_broker(self, broker_credentials: BrokerCredentials) -> List[Position]:
        """Synchronise les positions depuis un broker"""
        print(f"🔄 Synchronisation des positions depuis {broker_credentials.broker_type}")
        
        try:
            # Créer le broker
            broker = self.get_broker_instance(broker_credentials)
            
            # Récupérer les positions
            positions_data = broker.get_positions()
            print(f"📊 {len(positions_data)} positions récupérées")
            
            positions = []
            for i, pos_data in enumerate(positions_data):
                try:
                    # Gestion spéciale pour Binance
                    if broker_credentials.broker_type == 'binance':
                        # Binance retourne des balances avec asset, free, locked, total
                        asset_symbol = pos_data.get('asset', 'N/A')
                        position_size = float(pos_data.get('total', 0))
                        
                        if position_size <= 0:
                            continue  # Ignorer les balances nulles
                        
                        # Récupérer ou créer AssetType et Market pour Binance
                        asset_type, _ = AssetType.objects.get_or_create(name='Crypto')
                        market, _ = Market.objects.get_or_create(name='Binance')
                        
                        # Récupérer ou créer l'Asset sous-jacent
                        asset, _ = Asset.objects.get_or_create(
                            symbol=asset_symbol,
                            defaults={
                                'name': asset_symbol,
                                'sector': 'Cryptocurrency',
                                'industry': 'Digital Assets',
                                'market_cap': 0.0,
                                'price_history': 'xxxx',
                            }
                        )
                        
                        # Récupérer ou créer l'AssetTradable
                        asset_tradable, _ = AssetTradable.objects.get_or_create(
                            symbol=asset_symbol,
                            platform='binance',
                            defaults={
                                'asset': asset,
                                'name': asset_symbol,
                                'asset_type': asset_type,
                                'market': market,
                            }
                        )
                        
                        # Récupérer ou créer la Position
                        position, created = Position.objects.get_or_create(
                            user=broker_credentials.user,
                            asset_tradable=asset_tradable,
                            platform='binance',
                            defaults={
                                'size': Decimal(str(position_size)),
                                'entry_price': Decimal('0.0'),  # Pas de prix d'entrée pour les balances
                                'current_price': Decimal('0.0'),  # À récupérer si nécessaire
                                'side': 'BUY',  # Par défaut pour les balances
                                'status': 'OPEN',
                                'pnl': Decimal('0.0'),
                            }
                        )
                        
                        if not created:
                            # Mise à jour si la position existe déjà
                            position.size = Decimal(str(position_size))
                            position.save()
                        
                        positions.append(position)
                        print(f"✅ Position Binance synchronisée: {asset_symbol} {position_size}")
                        
                    else:
                        # Gestion pour les autres brokers (Saxo, etc.)
                        # Récupérer ou créer AssetType et Market
                        asset_type, _ = AssetType.objects.get_or_create(name=pos_data.get('type', 'Unknown'))
                        market, _ = Market.objects.get_or_create(name=pos_data.get('market', 'Unknown'))
                        
                        # Récupérer ou créer l'Asset sous-jacent
                        asset, _ = Asset.objects.get_or_create(
                            symbol=pos_data['symbol'],
                            defaults={
                                'name': pos_data.get('name', pos_data['symbol']),
                                'sector': pos_data.get('sector', 'xxxx'),
                                'industry': pos_data.get('industry', 'xxxx'),
                                'market_cap': pos_data.get('market_cap', 0.0),
                                'price_history': pos_data.get('price_history', 'xxxx'),
                            }
                        )
                        
                        # Pour Saxo, créer un AssetTradable unique pour chaque position
                        # en ajoutant un suffixe basé sur l'index
                        unique_symbol = f"{pos_data['symbol']}_{i}" if broker_credentials.broker_type == 'saxo' else pos_data['symbol']
                        
                        # Récupérer ou créer l'AssetTradable
                        asset_tradable, _ = AssetTradable.objects.get_or_create(
                            symbol=unique_symbol,
                            platform=broker_credentials.broker_type,
                            defaults={
                                'asset': asset,
                                'name': pos_data.get('name', pos_data['symbol']),
                                'asset_type': asset_type,
                                'market': market,
                            }
                        )
                        
                        # Récupérer ou créer la Position
                        position, created = Position.objects.get_or_create(
                            user=broker_credentials.user,
                            asset_tradable=asset_tradable,
                            defaults={
                                'size': Decimal(str(pos_data.get('size', 0))),
                                'entry_price': Decimal(str(pos_data.get('entry_price', 0))),
                                'current_price': Decimal(str(pos_data.get('current_price', 0))),
                                'side': pos_data.get('side', 'BUY'),
                                'status': pos_data.get('status', 'OPEN'),
                                'pnl': Decimal(str(pos_data.get('pnl', 0))),
                            }
                        )
                        
                        if not created:
                            # Mise à jour si la position existe déjà
                            position.size = Decimal(str(pos_data.get('size', 0)))
                            position.entry_price = Decimal(str(pos_data.get('entry_price', 0)))
                            position.current_price = Decimal(str(pos_data.get('current_price', 0)))
                            position.side = pos_data.get('side', 'BUY')
                            position.status = pos_data.get('status', 'OPEN')
                            position.pnl = Decimal(str(pos_data.get('pnl', 0)))
                            position.save()
                        
                        positions.append(position)
                        
                except Exception as e:
                    print(f"❌ Erreur traitement position {pos_data}: {e}")
                    continue
            
            print(f"✅ {len(positions)} positions synchronisées avec succès")
            return positions
            
        except Exception as e:
            print(f"❌ Erreur synchronisation positions: {e}")
            return []
    
    def sync_trades_from_broker(self, broker_credentials: BrokerCredentials, limit: int = 100) -> List[Trade]:
        """Synchronise les trades depuis un broker"""
        print(f"🔄 Synchronisation des trades depuis {broker_credentials.broker_type}")
        
        try:
            # Créer le broker
            broker = self.get_broker_instance(broker_credentials)
            
            # Récupérer les trades
            trades_data = broker.get_trades(limit)
            print(f"📊 {len(trades_data)} trades récupérés")
            
            trades = []
            for trade_data in trades_data:
                try:
                    # Récupérer ou créer AssetType et Market
                    asset_type, _ = AssetType.objects.get_or_create(name=trade_data.get('type', 'Unknown'))
                    market, _ = Market.objects.get_or_create(name=trade_data.get('market', 'Unknown'))
                    
                    # Récupérer ou créer l'Asset sous-jacent
                    asset, _ = Asset.objects.get_or_create(
                        symbol=trade_data['symbol'],
                        defaults={
                            'name': trade_data.get('name', trade_data['symbol']),
                            'sector': trade_data.get('sector', 'xxxx'),
                            'industry': trade_data.get('industry', 'xxxx'),
                            'market_cap': trade_data.get('market_cap', 0.0),
                            'price_history': trade_data.get('price_history', 'xxxx'),
                        }
                    )
                    
                    # Récupérer ou créer l'AssetTradable
                    asset_tradable, _ = AssetTradable.objects.get_or_create(
                        symbol=trade_data['symbol'],
                        platform=broker_credentials.broker_type,
                        defaults={
                            'asset': asset,
                            'name': trade_data.get('name', trade_data['symbol']),
                            'asset_type': asset_type,
                            'market': market,
                        }
                    )
                    
                    # Récupérer ou créer le Trade
                    trade, created = Trade.objects.get_or_create(
                        user=broker_credentials.user,
                        asset_tradable=asset_tradable,
                        timestamp=trade_data.get('timestamp'),
                        defaults={
                            'size': Decimal(str(trade_data.get('size', 0))),
                            'price': Decimal(str(trade_data.get('price', 0))),
                            'side': trade_data.get('side', 'BUY'),
                            'platform': broker_credentials.broker_type,
                        }
                    )
                    
                    if not created:
                        # Mise à jour si le trade existe déjà
                        trade.size = Decimal(str(trade_data.get('size', 0)))
                        trade.price = Decimal(str(trade_data.get('price', 0)))
                        trade.side = trade_data.get('side', 'BUY')
                        trade.platform = broker_credentials.broker_type
                        trade.save()
                    
                    trades.append(trade)
                    print(f"✅ Trade synchronisé: {trade.asset_tradable.symbol}")
                    
                except Exception as e:
                    print(f"❌ Erreur lors de la synchronisation du trade {trade_data.get('symbol', 'Unknown')}: {e}")
                    continue
            
            print(f"✅ Synchronisation terminée: {len(trades)} trades traités")
            return trades
            
        except Exception as e:
            print(f"❌ Erreur de synchronisation: {e}")
            raise
    
    def _process_broker_trade(self, broker_trade, broker_credentials, symbol=None):
        """Process a single broker trade and return created Trade objects"""
        created_trades = []
        
        try:
            # Determine the symbol from the trade data or parameter
            trade_symbol = symbol or broker_trade.get('symbol', 'UNKNOWN')
            print(f"  Traitement trade pour symbole: {trade_symbol}")
            
            # Create or retrieve the asset
            asset, _ = Asset.objects.get_or_create(
                symbol=trade_symbol,
                defaults={
                    'name': trade_symbol,
                    'type': 'CRYPTO' if broker_credentials.broker_type == 'binance' else 'STOCK',
                    'platform': broker_credentials.broker_type.upper(),
                }
            )
            
            # Determine side from Binance format or other formats
            side = 'BUY'
            if broker_credentials.broker_type == 'binance':
                side = 'BUY' if broker_trade.get('isBuyer', True) else 'SELL'
            else:
                side = broker_trade.get('side', 'BUY')
            
            # Create the trade
            trade = Trade.objects.create(
                user=self.user,
                asset=asset,
                size=Decimal(str(broker_trade.get('qty', broker_trade.get('size', 0)))),
                price=Decimal(str(broker_trade.get('price', 0))),
                side=side,
                platform=broker_credentials.broker_type.upper(),
            )
            
            created_trades.append(trade)
            print(f"    Trade créé: {trade.id} - {side} {trade.size} @ {trade.price}")
            
        except Exception as e:
            print(f"    Erreur lors du traitement du trade: {e}")
            print(f"    Données du trade: {broker_trade}")
        
        return created_trades
    
    def place_order(self, broker_credentials: BrokerCredentials, symbol: str, 
                   side: str, size: Decimal, order_type: str = "MARKET", 
                   price: Optional[Decimal] = None) -> Dict[str, Any]:
        """Placer un ordre via un courtier"""
        broker = self.get_broker_instance(broker_credentials)
        
        if not broker.authenticate():
            return {"error": "Échec de l'authentification"}
        
        return broker.place_order(symbol, side, size, order_type, price)
    
    def get_asset_price(self, broker_credentials: BrokerCredentials, symbol: str) -> Optional[Decimal]:
        """Récupérer le prix d'un actif depuis un courtier"""
        broker = self.get_broker_instance(broker_credentials)
        
        if not broker.authenticate():
            return None
        
        return broker.get_asset_price(symbol)

    def authenticate_saxo_with_code(self, broker_credentials: BrokerCredentials, authorization_code: str) -> bool:
        """Authentifier Saxo avec un code d'autorisation OAuth2"""
        if broker_credentials.broker_type != 'saxo':
            raise ValueError("Cette méthode est uniquement pour Saxo")
        
        broker = self.get_broker_instance(broker_credentials)
        return broker.authenticate_with_code(authorization_code)
    
    def get_saxo_auth_url(self, broker_credentials: BrokerCredentials, state: str = "xyz123") -> str:
        """Obtenir l'URL d'authentification Saxo"""
        if broker_credentials.broker_type != 'saxo':
            raise ValueError("Cette méthode est uniquement pour Saxo")
        
        broker = self.get_broker_instance(broker_credentials)
        return broker.get_auth_url(state)


class SaxoAuthService:
    """Service spécifique pour l'authentification Saxo"""
    
    @staticmethod
    def get_auth_url(client_id: str, redirect_uri: str, state: str = "xyz123") -> str:
        """Générer l'URL d'autorisation Saxo"""
        from urllib.parse import urlencode
        
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid",
            "state": state
        }
        return f"https://sim.logonvalidation.net/authorize?{urlencode(params)}"
    
    @staticmethod
    def exchange_code_for_tokens(authorization_code: str, client_id: str, 
                                client_secret: str, redirect_uri: str) -> Dict[str, Any]:
        """Échanger le code d'autorisation contre des tokens"""
        import requests
        
        token_url = "https://sim.logonvalidation.net/token"
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        return response.json() 