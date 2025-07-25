# 🏦 Intégration des Courtiers - Saxo Bank & Binance

## 📋 Vue d'ensemble

Cette structure modulaire permet d'intégrer facilement différents courtiers (Saxo Bank et Binance) dans votre application de trading Django. L'architecture est conçue pour être extensible et maintenir une interface commune.

## 🏗️ Architecture

### Structure des fichiers
```
trading_app/
├── brokers/
│   ├── __init__.py
│   ├── base.py          # Classe de base abstraite
│   ├── saxo.py          # Implémentation Saxo Bank
│   ├── binance.py       # Implémentation Binance
│   └── factory.py       # Factory pour créer les instances
├── models.py            # Modèle BrokerCredentials ajouté
├── services.py          # Services pour gérer les courtiers
├── views.py             # Vues pour l'interface utilisateur
└── templates/
    └── trading_app/
        ├── broker_dashboard.html
        └── broker_config.html
```

## 🔧 Configuration

### 1. Modèle BrokerCredentials

Le modèle `BrokerCredentials` stocke les informations d'authentification pour chaque courtier :

```python
class BrokerCredentials(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    broker_type = models.CharField(choices=[('saxo', 'Saxo Bank'), ('binance', 'Binance')])
    name = models.CharField(max_length=100)  # Nom pour identifier la config
    
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
```

### 2. Interface commune (BrokerBase)

Tous les courtiers implémentent la même interface :

```python
class BrokerBase(ABC):
    def authenticate(self) -> bool
    def refresh_auth_token(self) -> bool
    def get_accounts(self) -> List[Dict[str, Any]]
    def get_positions(self) -> List[Dict[str, Any]]
    def get_trades(self, limit: int = 100) -> List[Dict[str, Any]]
    def get_assets(self, asset_type: Optional[str] = None) -> List[Dict[str, Any]]
    def get_asset_price(self, symbol: str) -> Optional[Decimal]
    def place_order(self, symbol: str, side: str, size: Decimal, ...) -> Dict[str, Any]
    def cancel_order(self, order_id: str) -> bool
    def get_order_status(self, order_id: str) -> Dict[str, Any]
```

## 🔐 Authentification

### Saxo Bank (OAuth2)

1. **Configuration initiale** :
   - Créer une application dans le Saxo Developer Portal
   - Obtenir `client_id` et `client_secret`
   - Configurer `redirect_uri`

2. **Flow d'authentification** :
   ```python
   # 1. Générer l'URL d'autorisation
   auth_url = SaxoAuthService.get_auth_url(client_id, redirect_uri)
   
   # 2. L'utilisateur se connecte et est redirigé avec un code
   # 3. Échanger le code contre des tokens
   tokens = SaxoAuthService.exchange_code_for_tokens(code, client_id, client_secret, redirect_uri)
   
   # 4. Sauvegarder les tokens
   broker_creds.saxo_access_token = tokens['access_token']
   broker_creds.saxo_refresh_token = tokens['refresh_token']
   ```

### Binance (API Keys)

1. **Configuration** :
   - Créer des clés API dans l'interface Binance
   - Utiliser le testnet pour les tests
   - Configurer les permissions appropriées

2. **Authentification** :
   ```python
   # Les requêtes sont signées avec HMAC-SHA256
   signature = hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
   ```

## 🚀 Utilisation

### 1. Configuration d'un courtier

```python
from trading_app.services import BrokerService

# Créer une instance de service
broker_service = BrokerService(user)

# Récupérer les courtiers configurés
user_brokers = broker_service.get_user_brokers()

# Créer une instance de courtier
broker = broker_service.get_broker_instance(broker_credentials)
```

### 2. Synchronisation des données

```python
# Synchroniser les positions
positions = broker_service.sync_positions_from_broker(broker_creds)

# Synchroniser les trades
trades = broker_service.sync_trades_from_broker(broker_creds)
```

### 3. Placement d'ordres

```python
# Placer un ordre
result = broker_service.place_order(
    broker_creds,
    symbol="BTCUSDT",
    side="BUY",
    size=Decimal("0.001"),
    order_type="MARKET"
)
```

## 🌐 Interface utilisateur

### URLs disponibles

- `/brokers/` - Tableau de bord des courtiers
- `/brokers/config/` - Ajouter un nouveau courtier
- `/brokers/config/<id>/` - Modifier un courtier existant
- `/brokers/saxo/callback/` - Callback OAuth2 pour Saxo
- `/brokers/<id>/sync/` - Synchroniser les données
- `/brokers/<id>/order/` - Placer un ordre

### Fonctionnalités

1. **Tableau de bord** : Vue d'ensemble de tous les courtiers configurés
2. **Configuration** : Interface pour ajouter/modifier les credentials
3. **Synchronisation** : Boutons pour synchroniser positions et trades
4. **Authentification** : Gestion automatique des tokens OAuth2

## 🔄 Synchronisation automatique

### Tâches de fond (à implémenter)

```python
# management/commands/sync_brokers.py
from django.core.management.base import BaseCommand
from trading_app.services import BrokerService

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Synchroniser tous les courtiers actifs
        for broker_creds in BrokerCredentials.objects.filter(is_active=True):
            service = BrokerService(broker_creds.user)
            service.sync_positions_from_broker(broker_creds)
            service.sync_trades_from_broker(broker_creds)
```

## 🔒 Sécurité

### Bonnes pratiques

1. **Stockage sécurisé** : Les secrets sont stockés en base de données (à chiffrer en production)
2. **Tokens temporaires** : Les tokens Saxo expirent automatiquement
3. **Permissions minimales** : Utiliser les permissions minimales nécessaires pour les API Binance
4. **Testnet** : Utiliser le testnet Binance pour les tests

### Variables d'environnement

```bash
# Saxo Bank
SAXO_CLIENT_ID=your_client_id
SAXO_CLIENT_SECRET=your_client_secret
SAXO_REDIRECT_URI=http://localhost:8080/callback

# Binance
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
BINANCE_TESTNET=true
```

## 🧪 Tests

### Tests unitaires

```python
# tests/test_brokers.py
from django.test import TestCase
from trading_app.brokers.factory import BrokerFactory

class BrokerTestCase(TestCase):
    def test_saxo_broker_creation(self):
        credentials = {
            'client_id': 'test_id',
            'client_secret': 'test_secret'
        }
        broker = BrokerFactory.create_broker('saxo', user, credentials)
        self.assertIsInstance(broker, SaxoBroker)
```

## 📈 Extensions futures

### Courtiers supplémentaires

Pour ajouter un nouveau courtier :

1. Créer une nouvelle classe héritant de `BrokerBase`
2. Implémenter toutes les méthodes abstraites
3. Ajouter le type dans `BrokerFactory`
4. Mettre à jour le modèle `BrokerCredentials`

### Exemple pour Degiro

```python
class DegiroBroker(BrokerBase):
    def authenticate(self) -> bool:
        # Implémentation spécifique à Degiro
        pass
    
    # ... autres méthodes
```

## 🚨 Dépannage

### Problèmes courants

1. **Token Saxo expiré** : Utiliser `refresh_auth_token()`
2. **Erreur API Binance** : Vérifier les permissions des clés API
3. **Synchronisation échouée** : Vérifier la connectivité réseau

### Logs

```python
import logging
logger = logging.getLogger(__name__)

# Dans les méthodes des courtiers
logger.info(f"Synchronisation {broker_type} pour l'utilisateur {user.username}")
```

Cette architecture modulaire permet une intégration facile et maintenable de multiples courtiers tout en gardant une interface utilisateur cohérente. 