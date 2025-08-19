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
            self.auth_url = "https://live.logonvalidation.net"
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
        
        print(f"🔐 Authentification OAuth2 vers {token_url}")
        print(f"🔑 Client ID: {self.client_id}")
        print(f"🔑 Environment: {'LIVE' if 'live' in self.auth_url else 'SIMULATION'}")
        
        try:
            response = requests.post(
                token_url, 
                data=data, 
                timeout=30,
                headers={
                    'User-Agent': 'SaxoBroker/1.0',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code in [200, 201]:  # ✅ Accepter 200 et 201
                tokens = response.json()
                print("✅ Authentification réussie, traitement des tokens...")
                
                self.access_token = tokens["access_token"]
                self.refresh_token = tokens["refresh_token"]
                self.token_expires_at = datetime.now() + timedelta(seconds=tokens["expires_in"])
                
                print(f"🔑 Access Token: {self.access_token[:20]}...")
                print(f"🔑 Refresh Token: {self.refresh_token[:20]}...")
                print(f"⏰ Expire dans: {tokens.get('expires_in', 'N/A')} secondes")
                
                return True
            else:
                print(f"❌ Erreur HTTP: {response.status_code}")
                print(f"📄 Réponse: {response.text}")
                return False
                
        except requests.exceptions.ConnectTimeout:
            print(f"❌ Timeout de connexion vers {self.auth_url} (30s)")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Erreur de connexion vers {self.auth_url}")
            print(f"   Détail: {e}")
            return False
        except requests.exceptions.Timeout:
            print(f"❌ Timeout de la requête vers {self.auth_url}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur de requête vers {self.auth_url}")
            print(f"   Détail: {e}")
            return False
        except Exception as e:
            print(f"❌ Erreur inattendue lors de l'authentification: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def refresh_auth_token(self) -> bool:
        """Rafraîchir le token d'authentification avec gestion d'erreur robuste"""
        if not self.refresh_token:
            print("❌ Refresh token non disponible")
            return False
            
        token_url = f"{self.auth_url}/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        print(f"🔄 Tentative de refresh vers {token_url}")
        print(f"🔑 Client ID: {self.client_id}")
        print(f"🔑 Environment: {'LIVE' if 'live' in self.auth_url else 'SIMULATION'}")
        
        try:
            # Test de connectivité avec timeout et headers appropriés
            response = requests.post(
                token_url, 
                data=data, 
                timeout=30,
                headers={
                    'User-Agent': 'SaxoBroker/1.0',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code in [200, 201]:  # ✅ Accepter 200 et 201
                tokens = response.json()
                print("✅ Refresh réussi, traitement des tokens...")
            else:
                print(f"❌ Erreur HTTP: {response.status_code}")
                print(f"📄 Réponse: {response.text}")
                return False
            
            # Mettre à jour les tokens en mémoire
            self.access_token = tokens["access_token"]
            self.refresh_token = tokens["refresh_token"]
            self.token_expires_at = datetime.now() + timedelta(seconds=tokens["expires_in"])
            
            # Mettre à jour les tokens dans la base de données si possible
            try:
                from ..services import BrokerService
                broker_service = BrokerService(self.user)
                
                # Récupérer les credentials depuis la base de données
                from ..models import BrokerCredentials
                broker_creds = BrokerCredentials.objects.filter(
                    user=self.user,
                    saxo_access_token=self.credentials.get('access_token')
                ).first()
                
                if broker_creds:
                    # Mettre à jour avec les nouveaux tokens
                    new_tokens = {
                        'access_token': tokens["access_token"],
                        'refresh_token': tokens["refresh_token"],
                        'expires_in': tokens["expires_in"]
                    }
                    broker_service.update_saxo_tokens(broker_creds, new_tokens)
                    print("✅ Tokens mis à jour dans la base de données")
                else:
                    print("⚠️ Credentials non trouvés dans la base de données")
                    
            except Exception as e:
                print(f"⚠️ Erreur mise à jour base de données: {e}")
                # Continuer même si la mise à jour DB échoue
            
            return True
        except requests.exceptions.ConnectTimeout:
            print(f"❌ Timeout de connexion vers {self.auth_url} (30s)")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Erreur de connexion vers {self.auth_url}")
            print(f"   Détail: {e}")
            return False
        except requests.exceptions.Timeout:
            print(f"❌ Timeout de la requête vers {self.auth_url}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur de requête vers {self.auth_url}")
            print(f"   Détail: {e}")
            return False
        except Exception as e:
            print(f"❌ Erreur inattendue lors du refresh: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_connectivity(self) -> Dict[str, Any]:
        """Tester la connectivité vers les endpoints Saxo"""
        results = {}
        
        # Test de connectivité vers l'endpoint d'authentification
        try:
            print(f"🔍 Test de connectivité vers {self.auth_url}")
            response = requests.get(
                f"{self.auth_url}/authorize", 
                timeout=10,
                headers={'User-Agent': 'SaxoBroker/1.0'}
            )
            results['auth_endpoint'] = {
                'success': True,
                'status_code': response.status_code,
                'message': f"Connectivité OK vers {self.auth_url}"
            }
            print(f"✅ Endpoint d'authentification accessible: {response.status_code}")
        except Exception as e:
            results['auth_endpoint'] = {
                'success': False,
                'error': str(e),
                'message': f"Erreur de connectivité vers {self.auth_url}"
            }
            print(f"❌ Endpoint d'authentification inaccessible: {e}")
        
        # Test de connectivité vers l'API principale
        try:
            print(f"🔍 Test de connectivité vers {self.base_url}")
            response = requests.get(
                f"{self.base_url}/port/v1/accounts/me", 
                timeout=10,
                headers={'User-Agent': 'SaxoBroker/1.0'}
            )
            results['api_endpoint'] = {
                'success': True,
                'status_code': response.status_code,
                'message': f"Connectivité OK vers {self.base_url}"
            }
            print(f"✅ Endpoint API accessible: {response.status_code}")
        except Exception as e:
            results['api_endpoint'] = {
                'success': False,
                'error': str(e),
                'message': f"Erreur de connectivité vers {self.base_url}"
            }
            print(f"❌ Endpoint API inaccessible: {e}")
        
        return results
    
    def check_token_status(self) -> Dict[str, Any]:
        """Vérifier le statut du token d'authentification"""
        try:
            # Vérifier si on a un token
            if not self.access_token:
                return {
                    'valid': False,
                    'message': 'Aucun token disponible',
                    'expires_in': 'N/A'
                }
            
            # Gestion spéciale pour les tokens 24h
            if self.access_token and self.refresh_token and self.access_token == self.refresh_token:
                return {
                    'valid': True,
                    'message': 'Token 24h - pas d\'expiration',
                    'expires_in': '24h (pas d\'expiration)'
                }
            
            # Vérifier l'expiration
            if self.token_expires_at:
                now = datetime.now()
                if now < self.token_expires_at:
                    # Token valide, calculer le temps restant
                    time_left = self.token_expires_at - now
                    hours = int(time_left.total_seconds() // 3600)
                    minutes = int((time_left.total_seconds() % 3600) // 60)
                    
                    if hours > 0:
                        expires_in = f"{hours}h {minutes}m"
                    else:
                        expires_in = f"{minutes}m"
                    
                    return {
                        'valid': True,
                        'message': 'Token valide',
                        'expires_in': expires_in
                    }
                else:
                    return {
                        'valid': False,
                        'message': 'Token expiré',
                        'expires_in': 'Expiré'
                    }
            else:
                return {
                    'valid': False,
                    'message': 'Date d\'expiration inconnue',
                    'expires_in': 'N/A'
                }
                
        except Exception as e:
            return {
                'valid': False,
                'message': f'Erreur vérification: {str(e)}',
                'expires_in': 'N/A'
            }
    
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
                            'price_history': 'xxxx',
                            'SourceOrderId': base.get("SourceOrderId")  # Ajouter l'ID unique de la position
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
    
    def get_all_assets(self, limit: int = 1000) -> List[Dict]:
        """Récupère tous les actifs disponibles depuis Saxo"""
        try:
            if not self.access_token:
                print("❌ Pas de token d'accès Saxo")
                return []
            
            url = f"{self.base_url}/ref/v1/instruments/details"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "$top": limit,
                "AssetTypes": "Stock"  # Pour commencer avec les actions, peut être étendu
            }
            
            print(f"🔄 Récupération des actifs Saxo (limite: {limit})")
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                assets = data.get("Data", [])
                print(f"✅ {len(assets)} actifs récupérés depuis Saxo")
                return assets
            else:
                print(f"❌ Erreur API Saxo: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des actifs Saxo: {str(e)}")
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
        """Récupérer le solde du compte"""
        if not self.authenticate():
            return None
        
        try:
            # Utiliser l'endpoint direct pour les balances
            url = f"{self.base_url}/port/v1/balances/me"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
        
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Extraire les soldes selon la structure de l'API Saxo
            cash_balance = data.get('CashBalance', {})
            collateral_available = data.get('CollateralAvailable', {})
            
            # Formater les balances
            formatted_balances = {}
            
            # Ajouter le cash balance
            if isinstance(cash_balance, dict):
                for currency, amount in cash_balance.items():
                    formatted_balances[currency] = amount
            elif isinstance(cash_balance, (int, float)):
                formatted_balances['EUR'] = cash_balance
            
            # Ajouter le collateral si différent
            if isinstance(collateral_available, dict):
                for currency, amount in collateral_available.items():
                    if currency not in formatted_balances:
                        formatted_balances[currency] = amount
            elif isinstance(collateral_available, (int, float)):
                if 'EUR' not in formatted_balances:
                    formatted_balances['EUR'] = collateral_available
            
            print(f"📊 Balance Saxo récupérée: {formatted_balances}")
            print(f"💰 Cash: {cash_balance} | Collateral: {collateral_available}")
            return formatted_balances
                
        except Exception as e:
            print(f"❌ Erreur récupération balance Saxo: {e}")
            return None

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Récupérer les ordres en cours depuis Saxo"""
        if not self.authenticate():
            return []
        
        try:
            url = f"{self.base_url}/port/v1/orders/me"
            params = {
                "$skip": 0,
                "$top": 100,  # Limiter à 100 ordres
                "FieldGroups": "DisplayAndFormat",
                "Status": "Working"  # Seulement les ordres en cours
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            print(f"🔍 Récupération ordres Saxo: {url}")
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            orders = data.get("Data", [])
            
            print(f"📊 Ordres Saxo trouvés: {len(orders)}")
            
            formatted_orders = []
            for order in orders:
                formatted_order = {
                    'order_id': str(order.get('OrderId')),
                    'symbol': order.get('Symbol', ''),
                    'asset_type': order.get('AssetType', ''),
                    'uic': order.get('Uic'),
                    'order_type': order.get('OpenOrderType', ''),
                    'side': order.get('BuySell', ''),
                    'status': order.get('Status', ''),
                    'price': order.get('Price'),
                    'stop_price': order.get('StopPrice'),
                    'original_quantity': order.get('Amount'),
                    'executed_quantity': order.get('FilledAmount', 0),
                    'remaining_quantity': order.get('Amount', 0) - order.get('FilledAmount', 0),
                    'account_id': order.get('AccountId'),
                    'created_at': order.get('OrderTime'),
                    'expires_at': order.get('ExpiryTime'),
                    'broker_data': order  # Données brutes du broker
                }
                formatted_orders.append(formatted_order)
            
            return formatted_orders
            
        except Exception as e:
            print(f"Erreur récupération ordres en cours Saxo: {e}")
            return []
    
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