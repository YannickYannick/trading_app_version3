# 📱 Guide des Notifications Telegram

## 🎯 Vue d'ensemble

Votre application de trading envoie maintenant automatiquement des notifications Telegram à chaque fois que vous passez un ordre sur Saxo Bank ou Binance.

## 🚀 Fonctionnalités

### ✅ Notifications automatiques
- **Ordres placés** : Achat/Vente d'actifs
- **Erreurs d'ordres** : Problèmes lors du placement
- **Exécutions d'ordres** : Quand un ordre est exécuté

### 📊 Informations incluses
- **Symbole** de l'actif (ex: AAPL, BTCEUR)
- **Nom** de l'entreprise/actif
- **Prix** de l'ordre
- **Quantité** achetée/vendue
- **Type** d'ordre (Achat/Vente)
- **Broker** utilisé (Saxo/Binance)
- **Solde en cash** disponible
- **Timestamp** de l'action

## 🔧 Configuration

### Bot Telegram
- **Token** : `5492683283:AAER7boynSfnTlgKaG29XRA0fPgnjibXcWQ`
- **Chat ID** : `5582192940`
- **Statut** : ✅ Connecté et opérationnel

### Intégration
- **Fichier** : `trading_app/services/telegram_notifications.py`
- **Import** : Automatique dans toutes les vues d'ordres
- **Gestion d'erreurs** : Robustesse en cas de problème réseau

## 📱 Exemples de notifications

### 🟢 Ordre d'achat
```
🟢 NOUVEL ORDRE ACHAT 🟢

📊 Actif: AAPL
🏷️ Nom: Apple Inc.
💰 Prix: €150.5000
📈 Quantité: 10.0000
🏦 Broker: SAXO
💵 Cash disponible: €5000.00

⏰ 13/08/2025 23:55:30
```

### 🔴 Ordre de vente
```
🔴 NOUVEL ORDRE VENTE 🔴

📊 Actif: BTCEUR
🏷️ Nom: Bitcoin
💰 Prix: €45000.0000
📈 Quantité: 0.1000
🏦 Broker: BINANCE
💵 Cash disponible: €10000.00

⏰ 13/08/2025 23:56:15
```

### ❌ Erreur d'ordre
```
❌ ERREUR ORDRE ❌

📊 Actif: AAPL
🏦 Broker: SAXO
💥 Erreur: Token d'authentification expiré

⏰ 13/08/2025 23:57:00
```

## 🧪 Test des notifications

### Bouton de test
- **Page** : `/order/place/`
- **Bouton** : "Test Telegram" (bleu)
- **Action** : Envoie une notification de test

### URL de test directe
- **Endpoint** : `/test-telegram/`
- **Méthode** : GET
- **Authentification** : Requise

## 🔄 Intégration automatique

### Saxo Bank
- **Fonction** : `place_saxo_order_with_asset()`
- **Déclencheur** : Ordre placé avec succès
- **Déclencheur** : Erreur lors du placement

### Binance
- **Fonction** : `place_binance_order_with_asset()`
- **Déclencheur** : Ordre placé avec succès
- **Déclencheur** : Erreur lors du placement

## 🛠️ Personnalisation

### Modifier le message
Éditez `trading_app/services/telegram_notifications.py` :

```python
# Personnaliser l'emoji pour les achats
emoji = "🚀" if side == "BUY" else "🔴"

# Ajouter des informations personnalisées
message += f"📊 **P&L estimé:** €{estimated_pnl}\n"
```

### Ajouter de nouveaux types de notifications
```python
def send_custom_notification(self, data):
    """Notification personnalisée"""
    message = f"🎯 **{data['title']}**\n\n"
    message += f"📝 {data['description']}\n"
    # ... personnalisation
```

## 🚨 Gestion des erreurs

### Erreurs courantes
- **Token expiré** : Vérifiez la validité du bot
- **Chat ID incorrect** : Vérifiez l'ID de votre chat
- **Problème réseau** : Vérifiez votre connexion internet

### Logs
- **Fichier** : Logs Django standard
- **Niveau** : INFO pour les succès, ERROR pour les échecs
- **Format** : `Notification Telegram envoyée pour l'ordre {symbol} {side}`

## 📈 Améliorations futures

### Fonctionnalités prévues
- [ ] Notifications de prix en temps réel
- [ ] Alertes de seuils de P&L
- [ ] Rapports quotidiens de trading
- [ ] Notifications de stratégies automatisées

### Intégrations possibles
- [ ] Discord
- [ ] Slack
- [ ] Email
- [ ] SMS

## 🆘 Support

### Problèmes courants
1. **Pas de notification reçue**
   - Vérifiez que le bot est démarré
   - Vérifiez votre Chat ID
   - Testez avec le bouton "Test Telegram"

2. **Notifications en double**
   - Vérifiez les logs Django
   - Évitez de cliquer plusieurs fois sur "Passer l'ordre"

3. **Format des messages incorrect**
   - Vérifiez la syntaxe Markdown
   - Testez avec des données simples

### Contact
- **Logs** : Vérifiez la console Django
- **Test** : Utilisez le bouton de test
- **Debug** : Activez le mode DEBUG dans Django

---

**🎉 Votre système de notifications Telegram est maintenant opérationnel !**

Recevez des alertes instantanées sur votre téléphone à chaque ordre de trading.
