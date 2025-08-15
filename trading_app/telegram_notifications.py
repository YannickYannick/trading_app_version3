import requests
import json
from datetime import datetime
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Service de notifications Telegram pour l'application de trading"""
    
    def __init__(self):
        # Configuration du bot Telegram
        self.bot_token = "5492683283:AAER7boynSfnTlgKaG29XRA0fPgnjibXcWQ"
        self.chat_id = "5582192940"
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
    def send_message(self, message, parse_mode="Markdown"):
        """Envoie un message Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                logger.info(f"Message Telegram envoyé avec succès")
                return True
            else:
                logger.error(f"Erreur Telegram API: {result}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur réseau Telegram: {e}")
            return False
        except Exception as e:
            logger.error(f"Erreur générale Telegram: {e}")
            return False
    
    def send_order_notification(self, data):
        """Envoie une notification d'ordre de trading"""
        try:
            # Déterminer l'emoji selon le type d'ordre
            emoji = "🟢" if data.get('side', '').upper() == 'BUY' else "🔴"
            action = "ACHAT" if data.get('side', '').upper() == 'BUY' else "VENTE"
            
            # Vérifier si c'est une stratégie ou un ordre manuel
            is_strategy = 'strategy' in data
            
            if is_strategy:
                # Message pour les stratégies
                message = f"🤖 **STRATÉGIE EXÉCUTÉE** 🤖\n\n"
                message += f"📊 **Actif:** {data.get('symbol', 'N/A')}\n"
                message += f"🏷️ **Nom:** {data.get('asset_name', 'N/A')}\n"
                message += f"💰 **Prix:** €{data.get('price', 'N/A')}\n"
                message += f"📈 **Quantité:** {data.get('quantity', 'N/A')}\n"
                message += f"🏦 **Broker:** {data.get('broker', 'N/A')}\n"
                message += f"🎯 **Stratégie:** {data.get('strategy', 'N/A')}\n"
                message += f"📋 **Action:** {action}\n"
            else:
                # Message pour les ordres manuels
                message = f"{emoji} **NOUVEL ORDRE {action}** {emoji}\n\n"
                message += f"📊 **Actif:** {data.get('symbol', 'N/A')}\n"
                message += f"🏷️ **Nom:** {data.get('asset_name', 'N/A')}\n"
                message += f"💰 **Prix:** €{data.get('price', 'N/A')}\n"
                message += f"📈 **Quantité:** {data.get('quantity', 'N/A')}\n"
                message += f"🏦 **Broker:** {data.get('broker', 'N/A')}\n"
                
                # Ajouter le cash disponible si disponible
                if data.get('cash_available'):
                    message += f"💵 **Cash disponible:** €{data.get('cash_available', 'N/A')}\n"
            
            # Ajouter le timestamp
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            message += f"\n⏰ {timestamp}"
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la notification d'ordre: {e}")
            return False
    
    def send_error_notification(self, data):
        """Envoie une notification d'erreur de trading"""
        try:
            # Vérifier si c'est une stratégie ou un ordre manuel
            is_strategy = 'strategy' in data
            
            if is_strategy:
                # Message pour les erreurs de stratégies
                message = f"🤖 **ERREUR STRATÉGIE** 🤖\n\n"
                message += f"📊 **Actif:** {data.get('symbol', 'N/A')}\n"
                message += f"🏦 **Broker:** {data.get('broker', 'N/A')}\n"
                message += f"🎯 **Stratégie:** {data.get('strategy', 'N/A')}\n"
                message += f"💥 **Erreur:** {data.get('error_message', 'Erreur inconnue')}\n"
            else:
                # Message pour les erreurs d'ordres manuels
                message = f"❌ **ERREUR ORDRE** ❌\n\n"
                message += f"📊 **Actif:** {data.get('symbol', 'N/A')}\n"
                message += f"🏦 **Broker:** {data.get('broker', 'N/A')}\n"
                message += f"💥 **Erreur:** {data.get('error_message', 'Erreur inconnue')}\n"
            
            # Ajouter le timestamp
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            message += f"\n⏰ {timestamp}"
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la notification d'erreur: {e}")
            return False
    
    def send_test_notification(self):
        """Envoie une notification de test"""
        try:
            message = "🧪 **TEST TELEGRAM** 🧪\n\n"
            message += "✅ Votre bot Telegram est connecté et fonctionnel !\n"
            message += "📱 Vous recevrez maintenant des notifications pour tous vos ordres de trading.\n\n"
            
            # Ajouter le timestamp
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            message += f"⏰ {timestamp}"
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la notification de test: {e}")
            return False
    
    def test_connection(self):
        """Teste la connexion au bot Telegram"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                bot_info = result.get('result', {})
                logger.info(f"Bot Telegram connecté: {bot_info.get('first_name', 'N/A')}")
                return True
            else:
                logger.error(f"Erreur de connexion Telegram: {result}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur réseau lors du test de connexion: {e}")
            return False
        except Exception as e:
            logger.error(f"Erreur générale lors du test de connexion: {e}")
            return False

# Instance globale du notificateur Telegram
telegram_notifier = TelegramNotifier()
