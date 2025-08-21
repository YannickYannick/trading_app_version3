from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from trading_app.models import BrokerCredentials
from trading_app.services import BrokerService
from trading_app.telegram_notifications import TelegramNotifier
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Rafraîchir automatiquement les tokens des brokers Saxo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Nom d\'utilisateur spécifique (optionnel)'
        )
        parser.add_argument(
            '--broker',
            type=str,
            choices=['saxo', 'binance', 'all'],
            default='all',
            help='Type de broker à rafraîchir'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forcer le refresh même si le token n\'est pas expiré'
        )

    def handle(self, *args, **options):
        self.stdout.write("🔄 Démarrage du refresh automatique des tokens...")
        
        # Récupérer les utilisateurs
        if options['user']:
            try:
                users = [User.objects.get(username=options['user'])]
                self.stdout.write(f"👤 Utilisateur spécifique: {options['user']}")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ Utilisateur {options['user']} non trouvé"))
                return
        else:
            users = User.objects.filter(is_active=True)
            self.stdout.write(f"👥 {users.count()} utilisateurs actifs trouvés")

        # Filtrer par type de broker
        broker_type = options['broker']
        
        total_refreshed = 0
        total_errors = 0
        
        for user in users:
            self.stdout.write(f"\n🔍 Traitement de l'utilisateur: {user.username}")
            
            # Récupérer les credentials du broker
            if broker_type == 'all':
                credentials = BrokerCredentials.objects.filter(
                    user=user,
                    broker_type__in=['saxo', 'binance']
                )
            else:
                credentials = BrokerCredentials.objects.filter(
                    user=user,
                    broker_type=broker_type
                )
            
            if not credentials.exists():
                self.stdout.write(f"⚠️ Aucun credential {broker_type} trouvé pour {user.username}")
                continue
            
            for cred in credentials:
                try:
                    self.stdout.write(f"  🔑 Broker: {cred.broker_type}")
                    
                    if cred.broker_type == 'saxo':
                        success = self._refresh_saxo_tokens(user, cred, options['force'])
                    elif cred.broker_type == 'binance':
                        success = self._refresh_binance_tokens(user, cred, options['force'])
                    else:
                        self.stdout.write(f"    ⚠️ Type de broker non supporté: {cred.broker_type}")
                        continue
                    
                    if success:
                        total_refreshed += 1
                        self.stdout.write(self.style.SUCCESS(f"    ✅ Refresh réussi"))
                    else:
                        total_errors += 1
                        self.stdout.write(self.style.ERROR(f"    ❌ Refresh échoué"))
                        
                except Exception as e:
                    total_errors += 1
                    self.stdout.write(self.style.ERROR(f"    ❌ Erreur: {str(e)}"))
                    logger.error(f"Erreur refresh tokens pour {user.username} - {cred.broker_type}: {e}")

        # Résumé final
        self.stdout.write(f"\n📊 Résumé du refresh automatique:")
        self.stdout.write(f"  ✅ Tokens rafraîchis: {total_refreshed}")
        self.stdout.write(f"  ❌ Erreurs: {total_errors}")
        
        # Notification Telegram si configurée
        try:
            notifier = TelegramNotifier()
            if total_refreshed > 0 or total_errors > 0:
                message = f"🔄 Refresh automatique des tokens terminé\n"
                message += f"✅ Succès: {total_refreshed}\n"
                message += f"❌ Erreurs: {total_errors}"
                notifier.send_notification(message)
        except Exception as e:
            self.stdout.write(f"⚠️ Erreur notification Telegram: {e}")

    def _refresh_saxo_tokens(self, user, cred, force=False):
        """Rafraîchir les tokens Saxo"""
        try:
            broker_service = BrokerService(user)
            
            # Vérifier si le refresh est nécessaire
            if not force and not broker_service._should_refresh_saxo_tokens(cred):
                self.stdout.write(f"    ℹ️ Refresh non nécessaire pour {user.username}")
                return True
            
            # Tenter le refresh
            success = broker_service.refresh_saxo_tokens(cred)
            
            if success:
                self.stdout.write(f"    🔄 Tokens Saxo rafraîchis pour {user.username}")
            else:
                self.stdout.write(f"    ❌ Échec refresh tokens Saxo pour {user.username}")
            
            return success
            
        except Exception as e:
            self.stdout.write(f"    ❌ Erreur refresh Saxo: {e}")
            return False

    def _refresh_binance_tokens(self, user, cred, force=False):
        """Rafraîchir les tokens Binance (si applicable)"""
        try:
            # Pour Binance, on vérifie juste la validité des clés
            broker_service = BrokerService(user)
            
            # Test de connectivité
            success = broker_service.test_binance_connection(cred)
            
            if success:
                self.stdout.write(f"    ✅ Connexion Binance OK pour {user.username}")
            else:
                self.stdout.write(f"    ❌ Connexion Binance échouée pour {user.username}")
            
            return success
            
        except Exception as e:
            self.stdout.write(f"    ❌ Erreur test Binance: {e}")
            return False
