"""
Services pour gérer les interactions avec les courtiers
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.contrib.auth.models import User
from .brokers.factory import BrokerFactory
from .models import BrokerCredentials, Asset, Trade, Position


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
        """Synchroniser les positions depuis un courtier"""
        print(f"=== DEBUG SERVICE - Début sync_positions ===")
        print(f"Broker: {broker_credentials.broker_type}")
        
        broker = self.get_broker_instance(broker_credentials)
        print(f"Instance broker créée: {type(broker)}")
        
        # Gestion spéciale pour Saxo (OAuth2)
        if broker_credentials.broker_type == 'saxo':
            if not broker.is_authenticated():
                print("Saxo non authentifié - nécessite un code d'autorisation OAuth2")
                raise Exception("Saxo nécessite une authentification OAuth2. Veuillez d'abord vous authentifier via l'interface d'authentification.")
        
        if not broker.authenticate():
            print("Échec de l'authentification")
            return []
        
        print("Authentification réussie, récupération des positions...")
        broker_positions = broker.get_positions()
        print(f"Positions récupérées du broker: {len(broker_positions)}")
        print(f"Détail des positions: {broker_positions}")
        
        created_positions = []
        
        for broker_pos in broker_positions:
            print(f"Traitement position: {broker_pos}")
            
            # Créer ou récupérer l'asset
            asset, _ = Asset.objects.get_or_create(
                symbol=broker_pos.get('symbol', 'UNKNOWN'),
                defaults={
                    'name': broker_pos.get('symbol', 'UNKNOWN'),
                    'type': 'CRYPTO' if broker_credentials.broker_type == 'binance' else 'STOCK',
                    'platform': broker_credentials.broker_type.upper(),
                    'last_price': float(broker_pos.get('current_price', 0)),
                }
            )
            
            print(f"Asset: {asset}")
            
            # Créer ou mettre à jour la position
            position, created = Position.objects.get_or_create(
                user=self.user,
                asset=asset,
                defaults={
                    'size': Decimal(str(broker_pos.get('size', 0))),
                    'entry_price': Decimal(str(broker_pos.get('entry_price', 0))),
                    'current_price': Decimal(str(broker_pos.get('current_price', 0))),
                    'side': broker_pos.get('side', 'BUY'),
                    'status': 'OPEN',
                    'pnl': Decimal(str(broker_pos.get('pnl', 0))),
                }
            )
            
            if not created:
                # Mettre à jour la position existante
                position.size = Decimal(str(broker_pos.get('size', 0)))
                position.current_price = Decimal(str(broker_pos.get('current_price', 0)))
                position.pnl = Decimal(str(broker_pos.get('pnl', 0)))
                position.save()
            
            created_positions.append(position)
            print(f"Position {'créée' if created else 'mise à jour'}: {position}")
        
        print(f"=== FIN DEBUG SERVICE - {len(created_positions)} positions traitées ===")
        return created_positions
    
    def sync_trades_from_broker(self, broker_credentials: BrokerCredentials, limit: int = 100) -> List[Trade]:
        """Synchroniser les trades depuis un courtier"""
        print(f"=== DEBUG SERVICE - Début sync_trades ===")
        print(f"Broker: {broker_credentials.broker_type}")
        
        broker = self.get_broker_instance(broker_credentials)
        print(f"Instance broker créée: {type(broker)}")
        
        if not broker.authenticate():
            print("Échec de l'authentification")
            return []
        
        print("Authentification réussie, récupération des trades...")
        broker_trades = broker.get_trades(limit=limit)
        print(f"Trades récupérés du broker: {type(broker_trades)}")
        print(f"Contenu des trades: {broker_trades}")
        
        created_trades = []
        
        # Handle different return formats from brokers
        if isinstance(broker_trades, dict):
            # Binance returns a dict with symbols as keys and lists of trades as values
            print("Format détecté: dictionnaire (Binance)")
            for symbol, trades_list in broker_trades.items():
                print(f"Traitement du symbole: {symbol} ({len(trades_list)} trades)")
                for broker_trade in trades_list:
                    created_trades.extend(self._process_broker_trade(broker_trade, broker_credentials, symbol))
        elif isinstance(broker_trades, list):
            # Other brokers might return a flat list
            print("Format détecté: liste (Saxo)")
            for broker_trade in broker_trades:
                created_trades.extend(self._process_broker_trade(broker_trade, broker_credentials))
        else:
            print(f"Format inattendu: {type(broker_trades)}")
            return []
        
        print(f"=== FIN DEBUG SERVICE - {len(created_trades)} trades créés ===")
        return created_trades
    
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