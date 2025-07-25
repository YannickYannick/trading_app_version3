"""
Factory pour créer les instances de courtiers
"""

from typing import Dict, Any
from django.contrib.auth.models import User
from .base import BrokerBase
from .saxo import SaxoBroker
from .binance import BinanceBroker


class BrokerFactory:
    """Factory pour créer des instances de courtiers"""
    
    @staticmethod
    def create_broker(broker_type: str, user: User, credentials: Dict[str, Any]) -> BrokerBase:
        """
        Créer une instance de courtier selon le type
        
        Args:
            broker_type: Type de courtier ('saxo', 'binance')
            user: Utilisateur Django
            credentials: Dictionnaire des credentials
            
        Returns:
            Instance du courtier approprié
        """
        broker_type = broker_type.lower()
        
        if broker_type == 'saxo':
            return SaxoBroker(user, credentials)
        elif broker_type == 'binance':
            return BinanceBroker(user, credentials)
        else:
            raise ValueError(f"Type de courtier non supporté: {broker_type}")
    
    @staticmethod
    def get_supported_brokers() -> Dict[str, str]:
        """Retourner la liste des courtiers supportés"""
        return {
            'saxo': 'Saxo Bank',
            'binance': 'Binance'
        } 