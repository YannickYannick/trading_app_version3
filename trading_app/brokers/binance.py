"""
Implémentation du courtier Binance
Basé sur l'API Binance REST
"""

import requests
import hmac
import hashlib
import time
from datetime import datetime, timedelta
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

    def _make_request(self, method, endpoint, params=None, signed=False):
        """Fait une requête à l'API Binance"""
        url = f"{self.base_url}{endpoint}"
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['recvWindow'] = 5000
            query_string = urlencode(params)
            signature = hmac.new(
                self.api_secret,
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            params['signature'] = signature
            
        headers = {'X-MBX-APIKEY': self.api_key}
        
        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers)
            elif method == 'POST':
                response = requests.post(url, params=params, headers=headers)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Erreur API Binance: {e}")
            return None

    def get_balance(self):
        """Récupère le solde EUR et USD"""
        try:
            account_info = self._make_request('GET', '/api/v3/account', {}, signed=True)
            if account_info:
                balances = {}
                for balance in account_info.get('balances', []):
                    if balance['asset'] in ['EUR', 'USD']:
                        free = float(balance['free'])
                        locked = float(balance['locked'])
                        total = free + locked
                        if total > 0:
                            balances[balance['asset']] = total
                return balances
        except Exception as e:
            print(f"❌ Erreur récupération solde Binance: {e}")
        return {}
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Récupérer les positions actuelles (balances non nulles)"""
        try:
            account_info = self._make_request('GET', '/api/v3/account', {}, signed=True)
            if not account_info:
                return []
            
            positions = []
            for balance in account_info.get('balances', []):
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    # Formater les données pour correspondre au template position_tabulator
                    positions.append({
                        'id': len(positions) + 1,  # ID temporaire
                        'asset_name': balance['asset'],
                        'asset_symbol': balance['asset'],
                        'underlying_asset_name': balance['asset'],
                        'size': str(total),
                        'entry_price': '0.00',  # Pas de prix d'entrée pour les balances
                        'current_price': '0.00',  # À récupérer si nécessaire
                        'side': 'BUY',  # Par défaut
                        'status': 'OPEN',
                        'pnl': '0.00',  # Pas de PnL pour les balances
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat(),
                        # Données originales Binance
                        'asset': balance['asset'],
                        'free': free,
                        'locked': locked,
                        'total': total
                    })
            
            print(f"🔍 {len(positions)} positions Binance trouvées")
            return positions
        
        except Exception as e:
            print(f"❌ Erreur récupération positions Binance: {e}")
            return []

    def get_traded_symbols(self):
        """1️⃣ Récupérer tous les symboles tradés (Spot)"""
        try:
            account_info = self._make_request('GET', '/api/v3/account', {}, signed=True)
            if not account_info:
                return []
                
            symbols_traded = set()
            
            # Récupérer tous les tickers disponibles
            all_tickers = self._make_request('GET', '/api/v3/ticker/24hr')
            if not all_tickers:
                return []

            # Créer un set de tous les symboles disponibles
            available_symbols = {ticker['symbol'] for ticker in all_tickers}
            
            # Pour chaque balance non-nulle, chercher les paires correspondantes
            for balance in account_info.get('balances', []):
                if float(balance['free']) > 0 or float(balance['locked']) > 0:
                    asset = balance['asset']
                    # Chercher toutes les paires contenant cet asset
                    for symbol in available_symbols:
                        if asset in symbol:
                            symbols_traded.add(symbol)
            
            print(f"🔍 {len(symbols_traded)} symboles tradés trouvés")
            return list(symbols_traded)
            
        except Exception as e:
            print(f"❌ Erreur récupération symboles tradés: {e}")
            return []
    
    def get_all_spot_trades(self):
        """2️⃣ Récupérer tous les trades Spot"""
        symbols = self.get_traded_symbols()
        all_trades = []
        
        print(f"📥 Récupération des trades pour {len(symbols)} symboles...")
        
        for symbol in symbols:
            try:
                params = {'symbol': symbol, 'limit': 1000}
                trades = self._make_request('GET', '/api/v3/myTrades', params, signed=True)
                if trades:
                    all_trades.extend(trades)
                    print(f"✅ {len(trades)} trades récupérés pour {symbol}")
                time.sleep(0.1)  # Éviter le rate-limiting
            except Exception as e:
                print(f"❌ Erreur trades {symbol}: {e}")
                continue
                
        print(f"📊 Total: {len(all_trades)} trades récupérés")
        return all_trades

    def get_all_spot_orders(self):
        """3️⃣ Récupérer tous les orders Spot"""
        symbols = self.get_traded_symbols()
        all_orders = []
        
        print(f"📥 Récupération des orders pour {len(symbols)} symboles...")
        
        for symbol in symbols:
            try:
                params = {'symbol': symbol, 'limit': 1000}
                orders = self._make_request('GET', '/api/v3/allOrders', params, signed=True)
                if orders:
                    all_orders.extend(orders)
                    print(f"✅ {len(orders)} orders récupérés pour {symbol}")
                time.sleep(0.1)  # Éviter le rate-limiting
            except Exception as e:
                print(f"❌ Erreur orders {symbol}: {e}")
                continue
                
        print(f"📊 Total: {len(all_orders)} orders récupérés")
        return all_orders

    def get_convert_history(self, days=30):
        """4️⃣ Récupérer l'historique des conversions"""
        try:
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = end_time - (days * 24 * 60 * 60 * 1000)
            
            params = {
                'startTime': start_time,
                'endTime': end_time,
                'limit': 1000
            }
            
            convert_history = self._make_request('GET', '/sapi/v1/convert/trade/history', params, signed=True)
            if convert_history:
                print(f"✅ {len(convert_history.get('list', []))} conversions récupérées")
                return convert_history.get('list', [])
            return []
            
        except Exception as e:
            print(f"❌ Erreur convert history: {e}")
            return []

    def get_predefined_symbols_trades(self, symbols_list=None):
        """Récupérer les trades pour des symboles prédéfinis"""
        if symbols_list is None:
            # Symboles par défaut
            symbols_list = ['ETHEUR', 'BTCEUR', 'ADAEUR', 'AVAXEUR', 'SOLEUR']
        
        all_trades = []
        
        print(f"📥 Récupération des trades pour {len(symbols_list)} symboles prédéfinis...")
        
        for symbol in symbols_list:
            try:
                params = {'symbol': symbol, 'limit': 1000}
                trades = self._make_request('GET', '/api/v3/myTrades', params, signed=True)
                if trades:
                    all_trades.extend(trades)
                    print(f"✅ {len(trades)} trades récupérés pour {symbol}")
                time.sleep(0.1)  # Éviter le rate-limiting
            except Exception as e:
                print(f"❌ Erreur trades {symbol}: {e}")
                continue
                
        print(f"📊 Total: {len(all_trades)} trades récupérés pour symboles prédéfinis")
        return all_trades

    def get_trades(self, limit=50, mode="auto"):
        """
        Récupère l'historique des trades selon le mode choisi
        mode: "auto" (symboles tradés), "predefined" (symboles prédéfinis), "all" (tout)
        """
        print(f"🔍 Récupération des trades Binance (mode: {mode})...")
        
        all_trades = []
        
        if mode == "auto":
            # Mode automatique : symboles tradés
            trades = self.get_all_spot_trades()
            all_trades.extend(trades)
            
        elif mode == "predefined":
            # Mode symboles prédéfinis
            trades = self.get_predefined_symbols_trades()
            all_trades.extend(trades)
            
        elif mode == "all":
            # Mode complet : tout
            trades = self.get_all_spot_trades()
            all_trades.extend(trades)
            
            orders = self.get_all_spot_orders()
            all_trades.extend(orders)
            
            convert_history = self.get_convert_history(days=365)
            all_trades.extend(convert_history)
        
        # Formater les trades pour l'affichage
        formatted_trades = []
        for trade in all_trades[:limit]:
            try:
                if 'symbol' in trade:  # Trade ou Order
                    formatted_trade = {
                        'broker_name': 'Binance',
                        'broker_type': 'binance',
                        'environment': 'live',
                        'symbol': trade.get('symbol', 'N/A'),
                        'type': 'Spot',
                        'direction': 'BUY' if trade.get('isBuyer', trade.get('side')) == 'BUY' else 'SELL',
                        'size': float(trade.get('qty', trade.get('executedQty', 0))),
                        'opening_price': float(trade.get('price', 0)),
                        'closing_price': float(trade.get('price', 0)),
                        'profit_loss': 0,  # À calculer si nécessaire
                        'profit_loss_ratio': 0,
                        'opening_date': datetime.fromtimestamp(trade.get('time', 0) / 1000).strftime('%Y-%m-%d'),
                        'timestamp': datetime.fromtimestamp(trade.get('time', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    }
                elif 'fromAsset' in trade:  # Convert history
                    formatted_trade = {
                        'broker_name': 'Binance',
                        'broker_type': 'binance',
                        'environment': 'live',
                        'symbol': f"{trade.get('fromAsset', 'N/A')}→{trade.get('toAsset', 'N/A')}",
                        'type': 'Convert',
                        'direction': trade.get('side', 'N/A'),
                        'size': float(trade.get('toAmount', 0)),
                        'opening_price': float(trade.get('ratio', 0)),
                        'closing_price': float(trade.get('ratio', 0)),
                        'profit_loss': 0,
                        'profit_loss_ratio': 0,
                        'opening_date': datetime.fromtimestamp(trade.get('createTime', 0) / 1000).strftime('%Y-%m-%d'),
                        'timestamp': datetime.fromtimestamp(trade.get('createTime', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    }
                else:
                    continue
                
                formatted_trades.append(formatted_trade)
                
            except Exception as e:
                print(f"❌ Erreur formatage trade: {e}")
                continue

        print(f"✅ {len(formatted_trades)} trades formatés")
        return formatted_trades
    
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
        """Convertit un timestamp millisecondes en string datetime"""
        try:
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S') 