"""
Implémentation du courtier Binance
Basé sur l'API Binance REST
"""

import requests
import hmac
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal
from urllib.parse import urlencode
from .base import BrokerBase


class BinanceBroker(BrokerBase):
    """Client pour l'API Binance"""
    
    def __init__(self, user, credentials: Dict[str, Any]):
        super().__init__(user, credentials)
        self.api_key = credentials.get('api_key')
        self.api_secret = credentials.get('api_secret').encode('utf-8') if credentials.get('api_secret') else None
        self.base_url = "https://api.binance.com"  # ou "https://testnet.binance.vision" pour test
        self.is_testnet = credentials.get('testnet', False)
        
        if self.is_testnet:
            self.base_url = "https://testnet.binance.vision"
    
    def _get_server_time(self):
        """Récupérer le timestamp du serveur Binance"""
        try:
            url = f"{self.base_url}/api/v3/time"
            response = requests.get(url)
            return response.json()['serverTime']
        except Exception as e:
            print(f"Erreur récupération server time: {e}")
            return int(time.time() * 1000)
    
    def _sign_payload(self, params):
        """Signer les paramètres avec HMAC SHA256"""
        query_string = urlencode(params)
        signature = hmac.new(self.api_secret, query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        params['signature'] = signature
        return params
    
    def _get_headers(self):
        """Générer les headers d'authentification"""
        return {
            'X-MBX-APIKEY': self.api_key
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test simple de connexion à l'API Binance"""
        result = {
            "success": False,
            "message": "",
            "server_time": None,
            "exchange_info": None
        }
        
        try:
            # Test ping
            response = requests.get(f"{self.base_url}/api/v3/ping")
            response.raise_for_status()
            result["message"] += "Ping OK. "
            
            # Test server time
            server_time = self._get_server_time()
            result["server_time"] = server_time
            result["message"] += f"Server time: {server_time}. "
            
            # Test exchange info (public)
            response = requests.get(f"{self.base_url}/api/v3/exchangeInfo")
            response.raise_for_status()
            exchange_info = response.json()
            result["exchange_info"] = {
                "symbols_count": len(exchange_info.get("symbols", [])),
                "timezone": exchange_info.get("timezone"),
                "server_time": exchange_info.get("serverTime")
            }
            result["message"] += f"Exchange info OK ({len(exchange_info.get('symbols', []))} symbols). "
            
            result["success"] = True
            
        except Exception as e:
            result["message"] = f"Erreur: {e}"
            
        return result

    def authenticate(self) -> bool:
        """Authentification Binance (vérification des clés API)"""
        if not self.api_key or not self.api_secret:
            print("Clés API manquantes")
            return False
        
        # Test de connectivité d'abord
        try:
            response = requests.get(f"{self.base_url}/api/v3/ping")
            response.raise_for_status()
            print("Connectivité Binance OK")
        except Exception as e:
            print(f"Erreur connectivité Binance: {e}")
            return False
            
        # Test simple de l'API avec signature correcte
        try:
            endpoint = "/api/v3/account"
            timestamp = self._get_server_time()
            
            params = {
                "timestamp": timestamp,
                "recvWindow": 5000
            }
            
            signed_params = self._sign_payload(params)
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, headers=self._get_headers(), params=signed_params)
            
            if response.status_code == 200:
                print("Authentification Binance réussie")
                return True
            else:
                print(f"Erreur {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"Erreur authentification Binance: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Réponse serveur: {e.response.text}")
            return False
    
    def refresh_auth_token(self) -> bool:
        """Binance n'utilise pas de tokens, retourne True"""
        return True
    
    def get_accounts(self) -> List[Dict[str, Any]]:
        """Récupérer les informations du compte"""
        if not self.is_authenticated():
            return []
            
        try:
            endpoint = "/api/v3/account"
            timestamp = self._get_server_time()
            
            params = {
                "timestamp": timestamp,
                "recvWindow": 5000
            }
            
            signed_params = self._sign_payload(params)
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, headers=self._get_headers(), params=signed_params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Convertir en format standard
                accounts = []
                for balance in data.get("balances", []):
                    if float(balance.get("free", 0)) > 0 or float(balance.get("locked", 0)) > 0:
                        accounts.append({
                            "asset": balance.get("asset"),
                            "free": balance.get("free"),
                            "locked": balance.get("locked"),
                            "total": str(float(balance.get("free", 0)) + float(balance.get("locked", 0)))
                        })
                
                return accounts
            else:
                print(f"Erreur {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            print(f"Erreur récupération comptes Binance: {e}")
            return []
    def get_positions(self):
        """Récupérer les positions (balances) avec recherche multi-quote (EUR, USDT, BUSD)"""
        print("\n=== RÉCUPÉRATION DES POSITIONS ===")
        
        try:
            endpoint = "/api/v3/account"
            timestamp = self._get_server_time()

            params = {
                "timestamp": timestamp,
                "recvWindow": 5000
            }

            signed_params = self._sign_payload(params)
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, headers=self._get_headers(), params=signed_params)

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Données récupérées: {len(data.get('balances', []))} balances totales")

                positions = []
                for balance in data.get("balances", []):
                    free = float(balance.get("free", 0))
                    locked = float(balance.get("locked", 0))
                    total = free + locked
                    asset = balance.get("asset")

                    if total > 0:
                        print(f"🔎 {asset}: {total} (free: {free}, locked: {locked})")

                        symbol = None
                        price = None
                        for quote in ["EUR", "USDT", "BUSD"]:
                            symbol_try = f"{asset}{quote}"
                            price = self.get_asset_price(symbol_try)
                            if price:
                                symbol = symbol_try
                                break

                        if symbol and price:
                            position = {
                                "symbol": symbol,
                                "asset": asset,
                                "size": str(total),
                                "price": str(price),
                                "entry_price": str(price)  # Info approximative pour SPOT
                            }
                            positions.append(position)
                            print(f"  → Prix {symbol}: {price}")
                        else:
                            print(f"  → Aucun prix trouvé pour {asset} avec EUR/USDT/BUSD")
                
                print(f"\n📊 {len(positions)} positions avec prix trouvées")
                return positions
            else:
                print(f"❌ Erreur {response.status_code}: {response.text}")
                return []

        except Exception as e:
            print(f"❌ Erreur récupération positions: {e}")
            return []
    
    def get_trades(self, limit=50, symbols=None):
        """Récupérer les trades pour une liste de symboles"""
        print(f"\n=== RÉCUPÉRATION DES TRADES (limite: {limit} par symbole) ===")
        
        all_trades = {}
        total_trades = 0
        
        # Default symbols if none provided
        if symbols is None:
            symbols = ["BTCEUR", "ETHEUR"]

        try:
            for symbol in symbols:
                print(f"\n🔍 Symbol: {symbol}")
                endpoint = "/api/v3/myTrades"
                timestamp = self._get_server_time()

                params = {
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "recvWindow": 5000,
                    "limit": limit
                }

                signed_params = self._sign_payload(params)
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, headers=self._get_headers(), params=signed_params)

                if response.status_code == 200:
                    trades = response.json()
                    if trades:
                        total_trades += len(trades)
                        all_trades[symbol] = trades
                        print(f"✅ {len(trades)} trades récupérés pour {symbol}")
                        for i, trade in enumerate(trades[:5]):
                            direction = "BUY" if trade.get("isBuyer") else "SELL"
                            print(f"  • {i+1:02d}: {direction} {trade.get('qty')} @ {trade.get('price')}")
                    else:
                        print("⚠️ Aucun trade trouvé pour ce symbole")
                else:
                    print(f"❌ {symbol} - Erreur {response.status_code}: {response.text}")

            print(f"\n🎯 Total des trades récupérés: {total_trades}")
            return all_trades

        except Exception as e:
            print(f"❌ Erreur globale lors de la récupération des trades: {e}")
            return {}

    
    def get_assets(self, asset_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupérer les informations sur les paires de trading"""
        try:
            response = requests.get(f"{self.base_url}/api/v3/exchangeInfo")
            response.raise_for_status()
            data = response.json()
            
            assets = []
            for symbol_info in data.get("symbols", []):
                if symbol_info.get("status") == "TRADING":
                    assets.append({
                        "symbol": symbol_info.get("symbol"),
                        "baseAsset": symbol_info.get("baseAsset"),
                        "quoteAsset": symbol_info.get("quoteAsset"),
                        "status": symbol_info.get("status"),
                        "permissions": symbol_info.get("permissions")
                    })
            
            return assets
        except Exception as e:
            print(f"Erreur récupération actifs Binance: {e}")
            return []
    
    def get_asset_price(self, symbol: str) -> Optional[Decimal]:
        """Récupérer le prix d'un actif"""
        try:
            response = requests.get(f"{self.base_url}/api/v3/ticker/price", 
                              params={"symbol": symbol})
            response.raise_for_status()
            data = response.json()
            
            price = data.get("price")
            if price:
                return Decimal(price)
            
            return None
        except Exception as e:
            print(f"Erreur récupération prix Binance pour {symbol}: {e}")
            return None
    
    def place_order(self, symbol: str, side: str, size: Decimal, 
                   order_type: str = "MARKET", price: Optional[Decimal] = None) -> Dict[str, Any]:
        """Placer un ordre"""
        if not self.is_authenticated():
            return {"error": "Non authentifié"}
            
        try:
            endpoint = "/api/v3/order"
            timestamp = self._get_server_time()
            
            params = {
                "symbol": symbol,
                "side": side.upper(),
                "type": order_type,
                "quantity": str(size),
                "timestamp": timestamp,
                "recvWindow": 5000
            }
            
            if price and order_type.upper() == "LIMIT":
                params["price"] = str(price)
                params["timeInForce"] = "GTC"
            
            signed_params = self._sign_payload(params)
            url = f"{self.base_url}{endpoint}"
            response = requests.post(url, headers=self._get_headers(), params=signed_params)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Erreur {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"error": f"Erreur placement ordre Binance: {e}"}
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Annuler un ordre"""
        if not self.is_authenticated():
            return False
            
        try:
            endpoint = "/api/v3/order"
            timestamp = self._get_server_time()
            
            params = {
                "symbol": symbol,
                "orderId": order_id,
                "timestamp": timestamp,
                "recvWindow": 5000
            }
            
            signed_params = self._sign_payload(params)
            url = f"{self.base_url}{endpoint}"
            response = requests.delete(url, headers=self._get_headers(), params=signed_params)
            
            if response.status_code == 200:
                return True
            else:
                print(f"Erreur {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"Erreur annulation ordre Binance: {e}")
            return False
    
    def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Récupérer le statut d'un ordre"""
        if not self.is_authenticated():
            return {"error": "Non authentifié"}
            
        try:
            endpoint = "/api/v3/order"
            timestamp = self._get_server_time()
            
            params = {
                "symbol": symbol,
                "orderId": order_id,
                "timestamp": timestamp,
                "recvWindow": 5000
            }
            
            signed_params = self._sign_payload(params)
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, headers=self._get_headers(), params=signed_params)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Erreur {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"error": f"Erreur statut ordre Binance: {e}"} 

    def _convert_timestamp(self, timestamp_ms: int) -> str:
        """Convertir un timestamp millisecondes en date lisible"""
        from datetime import datetime
        dt_object = datetime.fromtimestamp(timestamp_ms / 1000)
        return dt_object.strftime('%Y-%m-%d %H:%M:%S') 