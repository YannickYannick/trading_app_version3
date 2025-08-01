"""
Implémentation du courtier Saxo Bank
Basé sur l'API Saxo OpenAPI
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from urllib.parse import urlencode
from .base import BrokerBase


class SaxoBroker(BrokerBase):
    """Client pour l'API Saxo Bank"""
    
    def __init__(self, user, credentials: Dict[str, Any]):
        super().__init__(user, credentials)
        self.client_id = credentials.get('client_id')
        self.client_secret = credentials.get('client_secret')
        self.redirect_uri = credentials.get('redirect_uri', 'http://localhost:8080/callback')
        
        # Déterminer l'environnement (live ou simulation)
        environment = credentials.get('environment', 'simulation')
        
        # Configurer les URLs selon l'environnement
        if environment == 'live':
            self.base_url = "https://gateway.saxobank.com/openapi"
            self.auth_url = "https://logonvalidation.net"
        else:  # simulation
            self.base_url = "https://gateway.saxobank.com/sim/openapi"
            self.auth_url = "https://sim.logonvalidation.net"
        
        # Récupérer les tokens stockés s'ils existent
        self.access_token = credentials.get('access_token')
        self.refresh_token = credentials.get('refresh_token')
        self.token_expires_at = credentials.get('token_expires_at')
        self.account_key = None  # Sera défini lors de l'authentification
    
    def get_auth_url(self, state: str = "xyz123") -> str:
        """Générer l'URL d'autorisation OAuth2"""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "openid",
            "state": state
        }
        return f"{self.auth_url}/authorize?{urlencode(params)}"
    
    def authenticate(self) -> bool:
        """Authentification - vérifier si on a un token valide ou essayer de le rafraîchir"""
        # Si on a déjà un token valide, on est authentifié
        if self.is_authenticated() and self.token_expires_at and datetime.now() < self.token_expires_at:
            return True
        
        # Gestion spéciale pour les tokens 24h
        # Si access_token et refresh_token sont identiques, c'est probablement un token 24h
        if self.access_token and self.refresh_token and self.access_token == self.refresh_token:
            print("🔑 Token 24h détecté - pas de refresh automatique")
            # Pour un token 24h, on ne tente jamais le refresh
            # On vérifie juste si le token existe
            return bool(self.access_token)
        
        # Pour Saxo Live, éviter le refresh automatique si on a déjà un token
        if 'sim' not in self.base_url and self.access_token:
            print("🔑 Saxo Live - Token existant, pas de refresh automatique")
            return bool(self.access_token)
        
        # Si on a un vrai refresh token (différent de l'access token), essayer de le rafraîchir
        if self.refresh_token and self.refresh_token != self.access_token:
            return self.refresh_auth_token()
        
        # Sinon, on n'est pas authentifié
        return False
    
    def authenticate_with_code(self, authorization_code: str) -> bool:
        """Authentification avec le code d'autorisation OAuth2"""
        token_url = f"{self.auth_url}/token"
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            tokens = response.json()
            
            self.access_token = tokens["access_token"]
            self.refresh_token = tokens["refresh_token"]
            self.token_expires_at = datetime.now() + timedelta(seconds=tokens["expires_in"])
            
            return True
        except Exception as e:
            print(f"Erreur d'authentification Saxo: {e}")
            return False
    
    def refresh_auth_token(self) -> bool:
        """Rafraîchir le token d'authentification"""
        if not self.refresh_token:
            return False
            
        token_url = f"{self.auth_url}/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            tokens = response.json()
            
            self.access_token = tokens["access_token"]
            self.refresh_token = tokens["refresh_token"]
            self.token_expires_at = datetime.now() + timedelta(seconds=tokens["expires_in"])
            
            return True
        except Exception as e:
            print(f"Erreur de rafraîchissement Saxo: {e}")
            return False
    
    def get_accounts(self) -> List[Dict[str, Any]]:
        """Récupérer les comptes de l'utilisateur"""
        if not self.is_authenticated():
            return []
            
        url = f"{self.base_url}/port/v1/accounts/me"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("Data", [])
        except Exception as e:
            print(f"Erreur récupération comptes Saxo: {e}")
            return []
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Récupère les positions depuis Saxo Bank"""
        print("🔍 Récupération des positions Saxo...")
        
        if not self.authenticate():
            print("❌ Échec de l'authentification Saxo")
            return []
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Utiliser l'endpoint correct pour les positions
            url = f"{self.base_url}/port/v1/positions/me"
            params = {"$top": 100}
            
            print(f"🌐 Appel API: {url}")
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                positions = data.get("Data", [])
                
                formatted_positions = []
                for i, pos in enumerate(positions):
                    try:
                        base = pos.get("PositionBase", {})
                        view = pos.get("PositionView", {})
                        
                        # Extraire les informations de base
                        uic = base.get("Uic")
                        asset_type = base.get("AssetType", "Stock")
                        amount = base.get("Amount", 0)
                        open_price = base.get("OpenPrice", 0)
                        
                        # Récupérer le nom et le symbole de l'instrument
                        instrument_name = self._get_instrument_name(uic, asset_type)
                        instrument_symbol = self._get_instrument_symbol(uic, asset_type)
                        
                        # Utiliser le vrai symbole ou l'UIC comme fallback
                        symbol = instrument_symbol if instrument_symbol else str(uic)
                        
                        # Formater selon le format attendu par le service
                        formatted_position = {
                            'symbol': symbol,
                            'name': instrument_name,
                            'type': asset_type,
                            'market': 'Saxo',
                            'size': float(amount) if amount else 0.0,
                            'entry_price': float(open_price) if open_price else 0.0,
                            'current_price': float(open_price) if open_price else 0.0,
                            'side': 'BUY' if float(amount) > 0 else 'SELL',
                            'status': base.get("Status", "OPEN"),
                            'pnl': float(view.get("ProfitLossOnTrade", 0)),
                            'sector': 'Unknown',
                            'industry': 'Unknown',
                            'market_cap': 0.0,
                            'price_history': 'xxxx'
                        }
                        
                        formatted_positions.append(formatted_position)
                        print(f"✅ Position formatée: {formatted_position['symbol']} - {formatted_position['name']}")
                        
                    except Exception as e:
                        print(f"❌ Erreur formatage position: {e}")
                        continue
                
                print(f"📊 {len(formatted_positions)} positions formatées")
                return formatted_positions
                
            else:
                print(f"❌ Erreur API Saxo: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Erreur récupération positions Saxo: {e}")
            return []

    def get_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Récupère l'historique des positions fermées depuis Saxo Bank"""
        print("🔍 Récupération de l'historique des positions fermées Saxo...")
        
        if not self.authenticate():
            print("❌ Échec de l'authentification Saxo")
            return []
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Récupérer les informations du compte et du client
            print("🔑 Récupération des informations du compte...")
            
            # Récupérer les comptes
            accounts_url = f"{self.base_url}/port/v1/accounts/me"
            accounts_response = requests.get(accounts_url, headers=headers)
            
            if accounts_response.status_code != 200:
                print(f"❌ Erreur récupération comptes: {accounts_response.status_code}")
                return []
            
            accounts_data = accounts_response.json()
            accounts = accounts_data.get("Data", [])
            
            if not accounts:
                print("❌ Aucun compte trouvé")
                return []
            
            account_id = accounts[0]["AccountId"]
            account_key = accounts[0]["AccountKey"]
            
            # Récupérer les informations du client
            clients_url = f"{self.base_url}/port/v1/clients/me"
            clients_response = requests.get(clients_url, headers=headers)
            
            if clients_response.status_code != 200:
                print(f"❌ Erreur récupération client: {clients_response.status_code}")
                return []
            
            clients_data = clients_response.json()
            client_key = clients_data["ClientKey"]
            
            print(f"🔑 Account ID: {account_id}")
            print(f"🔑 Client Key: {client_key}")
            print(f"🔑 Account Key: {account_key}")
            
            # Configuration de la période de recherche (30 derniers jours)
            from datetime import datetime, timezone, timedelta
            
            end_date = datetime.now(timezone.utc).date()
            start_date = (end_date - timedelta(days=30)).isoformat()
            end_date = end_date.isoformat()
            
            # Endpoint historique des positions fermées
            url = f"{self.base_url}/hist/v3/positions/{client_key}"
            
            params = {
                "AccountKey": account_key,
                "FromDate": start_date,
                "ToDate": end_date,
                "$top": limit
            }
            
            print(f"🌐 Appel API historique: {url}")
            print(f"📋 Params: {params}")
            
            response = requests.get(url, headers=headers, params=params)
            
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                positions = data.get('Data', [])
                
                print(f"📊 {len(positions)} positions fermées trouvées")
                
                formatted_trades = []
                for pos in positions:
                    try:
                        print(f"🔍 Traitement position fermée: {pos}")
                        
                        # Extraire les informations de la position fermée
                        instrument_symbol = pos.get('InstrumentSymbol', 'Unknown')
                        asset_type = pos.get('ClosingAssetType', 'Stock')
                        long_short = pos.get('LongShort', {})
                        direction = long_short.get('PresentationValue', 'Unknown') if long_short else 'Unknown'
                        amount = abs(pos.get('Amount', 0))
                        price_open = pos.get('PriceOpen', 0)
                        price_close = pos.get('PriceClose', 0)
                        opening_date = pos.get('OpeningTradeDate', '')
                        closing_date = pos.get('ClosingTradeDate', '')
                        profit_loss = pos.get('ProfitLoss', 0)
                        profit_loss_ratio = pos.get('ProfitLossAccountValueFraction', 0)
                        
                        # Déterminer le côté (BUY/SELL) basé sur la direction
                        side = 'BUY' if direction == 'Long' else 'SELL'
                        
                        # Formater selon le format attendu
                        formatted_trade = {
                            'symbol': instrument_symbol,
                            'name': instrument_symbol,  # On pourrait récupérer le nom via l'API si nécessaire
                            'type': asset_type,
                            'market': 'Saxo',
                            'size': float(amount) if amount else 0.0,
                            'price': float(price_close) if price_close else 0.0,
                            'side': side,
                            'timestamp': closing_date,
                            'opening_date': opening_date,
                            'opening_price': float(price_open) if price_open else 0.0,
                            'closing_price': float(price_close) if price_close else 0.0,
                            'profit_loss': float(profit_loss) if profit_loss else 0.0,
                            'profit_loss_ratio': float(profit_loss_ratio) if profit_loss_ratio else 0.0,
                            'direction': direction,
                            'sector': 'Unknown',
                            'industry': 'Unknown',
                            'market_cap': 0.0,
                            'price_history': 'xxxx'
                        }
                        
                        formatted_trades.append(formatted_trade)
                        print(f"✅ Position fermée formatée: {formatted_trade['symbol']} - {formatted_trade['direction']} - P&L: {formatted_trade['profit_loss']}")
                        
                    except Exception as e:
                        print(f"❌ Erreur formatage position fermée: {e}")
                        print(f"❌ Position data: {pos}")
                        continue
                
                print(f"📊 {len(formatted_trades)} positions fermées formatées")
                return formatted_trades
                
            else:
                print(f"❌ Erreur API historique Saxo: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Erreur récupération historique Saxo: {e}")
            return []
    
    def get_assets(self, asset_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupérer les actifs disponibles"""
        if not self.is_authenticated():
            return []
            
        url = f"{self.base_url}/ref/v1/instruments"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {}
        
        if asset_type:
            params["AssetTypes"] = asset_type
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("Data", [])
        except Exception as e:
            print(f"Erreur récupération actifs Saxo: {e}")
            return []
    
    def get_asset_price(self, symbol: str, uic: Optional[int] = None, 
                       asset_type: str = "Stock") -> Optional[Decimal]:
        """Récupérer le prix d'un actif"""
        if not self.is_authenticated():
            return None
            
        url = f"{self.base_url}/trade/v1/infoprices"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {
            "Uic": uic or self._get_uic_from_symbol(symbol),
            "AssetType": asset_type
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extraire le prix depuis la réponse
            quote = data.get("Quote", {})
            if quote:
                # Priorité: Ask > Mid > Bid
                price = quote.get("Ask") or quote.get("Mid") or quote.get("Bid")
                if price:
                    return Decimal(str(price))
            
            return None
        except Exception as e:
            print(f"Erreur récupération prix Saxo: {e}")
            return None
    
    def place_order(self, symbol: str, side: str, size: Decimal, 
                   order_type: str = "Market", price: Optional[Decimal] = None,
                   uic: Optional[int] = None, asset_type: str = "Stock") -> Dict[str, Any]:
        """Placer un ordre"""
        if not self.is_authenticated():
            return {"error": "Non authentifié"}
            
        accounts = self.get_accounts()
        if not accounts:
            return {"error": "Aucun compte trouvé"}
            
        account_key = accounts[0]["AccountKey"]  # Utiliser le premier compte
        
        url = f"{self.base_url}/trade/v1/orders"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        order_data = {
            "AccountKey": account_key,
            "Uic": uic or self._get_uic_from_symbol(symbol),
            "AssetType": asset_type,
            "BuySell": side.upper(),
            "Amount": float(size),
            "OrderType": order_type
        }
        
        if price and order_type.lower() == "limit":
            order_data["Price"] = float(price)
        
        try:
            response = requests.post(url, headers=headers, json=order_data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Erreur placement ordre Saxo: {e}"}
    
    def cancel_order(self, order_id: str) -> bool:
        """Annuler un ordre"""
        if not self.is_authenticated():
            return False
            
        url = f"{self.base_url}/trade/v1/orders/{order_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Erreur annulation ordre Saxo: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Récupérer le statut d'un ordre"""
        if not self.is_authenticated():
            return {"error": "Non authentifié"}
            
        url = f"{self.base_url}/trade/v1/orders/{order_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Erreur statut ordre Saxo: {e}"}
    
    def get_balance(self):
        """Retourne le solde cash du compte Saxo"""
        print(f"🔍 Récupération solde Saxo - Environnement: {'LIVE' if 'sim' not in self.base_url else 'SIMULATION'}")
        print(f"🔍 Base URL: {self.base_url}")
        
        if not self.authenticate():
            print("❌ Échec de l'authentification Saxo")
            return None
        
        print(f"✅ Authentification réussie - Token: {self.access_token[:20]}...")
        
        url = f"{self.base_url}/port/v1/balances/me"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        
        print(f"🌐 Appel API: {url}")
        print(f"📋 Headers: {headers}")
        
        try:
            response = requests.get(url, headers=headers)
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Réponse: {data}")
                cash_balance = data.get('CashBalance')
                print(f"💰 Cash Balance: {cash_balance}")
                return cash_balance
            else:
                print(f"❌ Erreur {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Erreur récupération solde Saxo: {e}")
            return None
    
    def _get_uic_from_symbol(self, symbol: str) -> Optional[int]:
        """Récupérer l'UIC d'un symbole"""
        assets = self.get_assets()
        for asset in assets:
            if asset.get("Symbol") == symbol:
                return asset.get("Identifier")
        return None 

    def set_24h_token(self, token: str):
        """Configurer un token 24h de Saxo"""
        self.access_token = token
        self.refresh_token = token  # Même token pour détecter que c'est un 24h token
        # Expiration dans 23h50 pour avoir une marge de sécurité
        self.token_expires_at = datetime.now() + timedelta(hours=23, minutes=50)
        print(f"🔑 Token 24h configuré - expire le {self.token_expires_at}")
    
    def is_24h_token(self) -> bool:
        """Vérifier si on utilise un token 24h"""
        return (self.access_token and self.refresh_token and 
                self.access_token == self.refresh_token) 

    def _get_instrument_name(self, uic: str, asset_type: str = "Stock") -> str:
        """Récupère le nom de l'instrument via l'API Saxo"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            
            # Utiliser l'endpoint correct pour les détails d'instrument
            url = f"{self.base_url}/ref/v1/instruments/details/{uic}/{asset_type.lower()}"
            
            print(f"🔍 Récupération nom instrument: {url}")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Réponse instrument: {data}")
                
                description = data.get("Description")
                symbol = data.get("Symbol")
                
                if description:
                    print(f"✅ Nom trouvé: {description} ({symbol})")
                    return description
                else:
                    print(f"⚠️ Pas de description trouvée pour UIC {uic}")
                    return f"Unknown {uic}"
            else:
                print(f"❌ Erreur API instrument: {response.status_code} - {response.text}")
                return f"Unknown {uic}"
            
        except Exception as e:
            print(f"❌ Erreur récupération nom instrument: {e}")
            return f"Unknown {uic}"

    def _get_instrument_symbol(self, uic: str, asset_type: str = "Stock") -> str:
        """Récupère le symbole de l'instrument via l'API Saxo"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            
            # Utiliser l'endpoint correct pour les détails d'instrument
            url = f"{self.base_url}/ref/v1/instruments/details/{uic}/{asset_type.lower()}"
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                symbol = data.get("Symbol")
                
                if symbol:
                    return symbol
                else:
                    return str(uic)
            else:
                return str(uic)
            
        except Exception as e:
            print(f"❌ Erreur récupération symbole instrument: {e}")
            return str(uic) 