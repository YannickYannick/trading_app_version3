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
        self.base_url = "https://gateway.saxobank.com/sim/openapi"  # ou "https://gateway.saxobank.com/openapi" pour prod
        self.auth_url = "https://sim.logonvalidation.net"  # ou "https://logonvalidation.net" pour prod
        
        # Récupérer les tokens stockés s'ils existent
        self.access_token = credentials.get('access_token')
        self.refresh_token = credentials.get('refresh_token')
        self.token_expires_at = credentials.get('token_expires_at')
    
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
        """Récupérer les positions ouvertes"""
        if not self.is_authenticated():
            return []
            
        # Récupérer d'abord les comptes
        accounts = self.get_accounts()
        if not accounts:
            return []
            
        all_positions = []

        for account in accounts:
            account_key = account.get("AccountKey")
            if account_key:
                url = f"{self.base_url}/port/v1/accounts/{account_key}/positions"
                headers = {"Authorization": f"Bearer {self.access_token}"}
                try:
                    positions_url = "https://gateway.saxobank.com/sim/openapi/port/v1/positions/me"
                    headers = {"Authorization": f"Bearer {self.access_token}","Content-Type": "application/json"}
                    params = {"$top": 100}

                    response = requests.get(positions_url, headers=headers, params=params)
                    response.raise_for_status()
                    data = response.json()
                    positions = data.get("Data", [])
                    all_positions.extend(positions)
                    print(" Yannick !!!")
                #try:
                    #response = requests.get(url, headers=headers)
                    #response.raise_for_status()
                    #data = response.json()
                    #positions = data.get("Data", [])
                    #all_positions.extend(positions)
                except Exception as e:
                    print(f"Erreur récupération positions Saxo: {e}")
        
        return all_positions
    
    def get_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Récupérer l'historique des trades"""
        if not self.is_authenticated():
            return []
            
        accounts = self.get_accounts()
        if not accounts:
            return []
            
        all_trades = []
        for account in accounts:
            account_key = account.get("AccountKey")
            if account_key:
                url = f"{self.base_url}/port/v1/trades/me"
                headers = {"Authorization": f"Bearer {self.access_token}"}
                params = {"$top": limit}
                print("vérification")
                print(url)
                print(headers)
                print(params)

                
                try:
                    response = requests.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    data = response.json()
                    trades = data.get("Data", [])
                    all_trades.extend(trades)
                    print(" Yannick !!! ooo 2")
                except Exception as e:
                    print(f"Erreur récupération trades Saxo: {e}")
        
        return all_trades
    
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