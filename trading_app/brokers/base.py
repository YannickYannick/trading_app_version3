"""
Classe de base abstraite pour tous les courtiers
Définit l'interface commune que tous les courtiers doivent implémenter
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.contrib.auth.models import User


class BrokerBase(ABC):
    """Classe de base abstraite pour tous les courtiers"""
    
    def __init__(self, user: User, credentials: Dict[str, Any]):
        self.user = user
        self.credentials = credentials
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authentification avec le courtier"""
        pass
    
    @abstractmethod
    def refresh_auth_token(self) -> bool:
        """Rafraîchir le token d'authentification"""
        pass
    
    @abstractmethod
    def get_accounts(self) -> List[Dict[str, Any]]:
        """Récupérer les comptes de l'utilisateur"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Récupérer les positions ouvertes"""
        pass
    
    @abstractmethod
    def get_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Récupérer l'historique des trades"""
        pass
    
    @abstractmethod
    def get_assets(self, asset_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupérer les actifs disponibles"""
        pass
    
    @abstractmethod
    def get_asset_price(self, symbol: str) -> Optional[Decimal]:
        """Récupérer le prix d'un actif"""
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, side: str, size: Decimal, 
                   order_type: str = "MARKET", price: Optional[Decimal] = None) -> Dict[str, Any]:
        """Placer un ordre"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Annuler un ordre"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Récupérer le statut d'un ordre"""
        pass
    
    def is_authenticated(self) -> bool:
        """Vérifier si l'authentification est valide"""
        return self.access_token is not None
    
    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Méthode utilitaire pour faire des requêtes HTTP"""
        import requests
        
        headers = kwargs.get('headers', {})
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json() 