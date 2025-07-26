# Guide d'utilisation des Tokens 24h Saxo

## 🔑 Qu'est-ce qu'un token 24h ?

Un token 24h de Saxo Bank est un token d'accès qui expire automatiquement après 24 heures. Contrairement au flux OAuth2 standard, il ne peut pas être rafraîchi via un refresh_token.

## ❌ Problème avec les tokens 24h

Si vous mettez un token 24h dans le champ `refresh_token`, le système tentera automatiquement de le rafraîchir, ce qui causera une erreur 401 Unauthorized car les tokens 24h ne supportent pas le refresh.

## ✅ Solution implémentée

### 1. Détection automatique
Le système détecte automatiquement si vous utilisez un token 24h en vérifiant si `access_token` et `refresh_token` sont identiques.

### 2. Pas de refresh automatique
Si un token 24h est détecté, le système n'essaie jamais de le rafraîchir automatiquement.

### 3. Interface utilisateur améliorée
- Checkbox "J'utilise un token 24h" pour copie automatique
- Détection automatique des tokens identiques
- Explications claires dans l'interface

## 📋 Comment configurer un token 24h

### Option 1 : Interface web (recommandée)

1. **Aller sur la configuration Saxo** (`/brokers/config/`)
2. **Remplir les champs obligatoires** :
   - Client ID
   - Client Secret  
   - Redirect URI
3. **Dans la section "Tokens manuels"** :
   - Cocher "J'utilise un token 24h"
   - Saisir votre token 24h dans "Access Token"
   - Le "Refresh Token" sera automatiquement copié
4. **Sauvegarder la configuration**

### Option 2 : Saisie manuelle

1. **Mettre le même token** dans les deux champs :
   - Access Token : `votre_token_24h`
   - Refresh Token : `votre_token_24h` (même valeur)
2. **Le système détectera automatiquement** qu'il s'agit d'un token 24h

### Option 3 : Code Python

```python
from trading_app.brokers.saxo import SaxoBroker

# Créer une instance avec token 24h
credentials = {
    'client_id': 'votre_client_id',
    'client_secret': 'votre_client_secret',
    'redirect_uri': 'http://localhost:8080/callback',
    'access_token': 'votre_token_24h',
    'refresh_token': 'votre_token_24h',  # Même token
}

broker = SaxoBroker(user, credentials)

# Ou utiliser la méthode dédiée
broker.set_24h_token('votre_token_24h')

# Vérifier si c'est un token 24h
if broker.is_24h_token():
    print("Token 24h détecté !")
```

## 🔍 Test de votre configuration

### Script de test automatique

```bash
python test_saxo_tokens.py
```

Ce script vérifiera :
- ✅ Présence des tokens
- ✅ Détection du token 24h
- ✅ Authentification réussie
- ✅ Récupération de données

### Test manuel

1. **Aller sur `/brokers/`**
2. **Cliquer sur "Test"** pour votre configuration Saxo
3. **Vérifier que l'authentification réussit**

## ⚠️ Limitations des tokens 24h

### Avantages
- ✅ Configuration simple
- ✅ Pas besoin de flux OAuth2 complet
- ✅ Idéal pour les tests et développement

### Inconvénients
- ❌ Expire après 24h (renouvellement manuel nécessaire)
- ❌ Pas de refresh automatique
- ❌ Moins sécurisé que le flux OAuth2 complet

## 🔄 Migration vers OAuth2 complet

Pour une utilisation en production, il est recommandé d'utiliser le flux OAuth2 complet :

1. **Aller sur `/brokers/`**
2. **Cliquer sur "Obtenir URL d'authentification Saxo"**
3. **Suivre le processus OAuth2**
4. **Les tokens seront automatiquement gérés**

## 🛠️ Dépannage

### Erreur 401 Unauthorized
- **Cause** : Tentative de refresh d'un token 24h
- **Solution** : Vérifier que `access_token` et `refresh_token` sont identiques

### Token expiré
- **Cause** : Token 24h expiré (> 24h)
- **Solution** : Générer un nouveau token 24h et le mettre à jour

### Pas de détection automatique
- **Cause** : Tokens différents dans les champs
- **Solution** : Mettre le même token dans les deux champs

## 📞 Support

Si vous rencontrez des problèmes :
1. Vérifiez les logs Django
2. Exécutez le script de test
3. Vérifiez la configuration dans l'interface web 