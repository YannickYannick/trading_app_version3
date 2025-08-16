"""
Management command pour le refresh automatique des tokens Saxo Bank
Fréquence configurable par broker (défaut: 45 minutes)
Retry automatique toutes les 3 minutes en cas d'échec (max 5 tentatives)
Historique des tentatives en base de données
Notifications Telegram uniquement pour les échecs
"""

import time
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from trading_app.models import BrokerCredentials, TokenRefreshHistory
from trading_app.brokers.factory import BrokerFactory
from trading_app.telegram_notifications import telegram_notifier


class Command(BaseCommand):
    help = 'Refresh automatique des tokens Saxo Bank selon la configuration de chaque broker'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simuler le refresh sans effectuer de changements'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forcer le refresh même si pas nécessaire'
        )
        parser.add_argument(
            '--broker-id',
            type=int,
            help='Refresh uniquement pour un broker spécifique'
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🔄 Démarrage du refresh automatique des tokens Saxo Bank...")
        
        dry_run = options['dry_run']
        force = options['force']
        broker_id = options.get('broker_id')
        
        if dry_run:
            self.stdout.write("🔍 Mode simulation activé - aucun changement effectué")
        
        # Récupérer les brokers Saxo activés pour l'auto-refresh
        brokers_query = BrokerCredentials.objects.filter(
            broker_type='saxo',
            auto_refresh_enabled=True
        )
        
        if broker_id:
            brokers_query = brokers_query.filter(id=broker_id)
            self.stdout.write(f"🎯 Refresh uniquement pour le broker ID: {broker_id}")
        
        brokers = list(brokers_query)
        
        if not brokers:
            self.stdout.write("⚠️ Aucun broker Saxo configuré pour l'auto-refresh")
            return
        
        self.stdout.write(f"📊 {len(brokers)} broker(s) Saxo trouvé(s) pour l'auto-refresh")
        
        total_refreshes = 0
        total_success = 0
        total_errors = 0
        
        for broker in brokers:
            try:
                self.stdout.write(f"\n🔍 Traitement du broker: {broker.name}")
                
                # Vérifier si un refresh est nécessaire
                if not force and not self._needs_refresh(broker):
                    self.stdout.write("  ⏭️ Refresh non nécessaire - token encore valide")
                    continue
                
                total_refreshes += 1
                
                if dry_run:
                    self.stdout.write("  🔍 [SIMULATION] Refresh simulé")
                    continue
                
                # Tenter le refresh avec retry
                success = self._refresh_token_with_retry(broker)
                
                if success:
                    total_success += 1
                    self.stdout.write("  ✅ Refresh réussi")
                else:
                    total_errors += 1
                    self.stdout.write("  ❌ Refresh échoué après tous les retry")
                    
            except Exception as e:
                total_errors += 1
                self.stdout.write(f"  💥 Erreur lors du traitement: {e}")
                self._log_refresh_attempt(broker, False, error_message=str(e))
        
        # Résumé final
        self.stdout.write(f"\n📊 Résumé du refresh automatique:")
        self.stdout.write(f"  🔄 Total des tentatives: {total_refreshes}")
        self.stdout.write(f"  ✅ Succès: {total_success}")
        self.stdout.write(f"  ❌ Échecs: {total_errors}")
        
        if total_errors > 0:
            self.stdout.write(self.style.ERROR("  ⚠️ Certains refresh ont échoué"))
        else:
            self.stdout.write(self.style.SUCCESS("  🎉 Tous les refresh ont réussi"))
    
    def _needs_refresh(self, broker):
        """Vérifier si un refresh est nécessaire pour ce broker"""
        if not broker.saxo_access_token:
            return True
        
        # Gestion spéciale pour les tokens 24h
        if (broker.saxo_access_token and broker.saxo_refresh_token and 
            broker.saxo_access_token == broker.saxo_refresh_token):
            # Token 24h - vérifier s'il expire bientôt
            if broker.saxo_token_expires_at:
                time_left = broker.saxo_token_expires_at - timezone.now()
                if time_left < timedelta(hours=1):  # Expire dans moins d'1h
                    return True
            return False
        
        # Token normal - vérifier s'il expire bientôt
        if broker.saxo_token_expires_at:
            time_left = broker.saxo_token_expires_at - timezone.now()
            # Refresh si moins de 80% de la durée de vie restante
            if time_left < timedelta(minutes=broker.auto_refresh_frequency * 0.8):
                return True
        
        return False
    
    def _refresh_token_with_retry(self, broker):
        """Tenter le refresh avec retry automatique"""
        max_retries = 5
        retry_delay = 3 * 60  # 3 minutes en secondes
        
        for attempt in range(max_retries + 1):
            try:
                self.stdout.write(f"  🔄 Tentative de refresh {attempt + 1}/{max_retries + 1}")
                
                # Créer l'instance du broker
                broker_instance = BrokerFactory.create_broker(broker)
                
                if not broker_instance:
                    error_msg = "Impossible de créer l'instance du broker"
                    self._log_refresh_attempt(broker, False, error_message=error_msg, retry_count=attempt)
                    continue
                
                # Tenter le refresh
                if broker_instance.refresh_auth_token():
                    # Succès - sauvegarder les nouveaux tokens
                    self._update_broker_tokens(broker, broker_instance)
                    self._log_refresh_attempt(broker, True, 
                                           new_access_token=broker_instance.access_token,
                                           new_refresh_token=broker_instance.refresh_token,
                                           expires_in=broker_instance.token_expires_at)
                    return True
                else:
                    # Échec du refresh
                    error_msg = "Refresh échoué"
                    self._log_refresh_attempt(broker, False, error_message=error_msg, retry_count=attempt)
                    
            except Exception as e:
                error_msg = f"Erreur lors du refresh: {str(e)}"
                self._log_refresh_attempt(broker, False, error_message=error_msg, retry_count=attempt)
            
            # Si ce n'est pas la dernière tentative, attendre avant de retry
            if attempt < max_retries:
                self.stdout.write(f"  ⏳ Attente de {retry_delay // 60} minutes avant retry...")
                time.sleep(retry_delay)
        
        # Toutes les tentatives ont échoué
        self._notify_refresh_failure(broker, max_retries)
        return False
    
    def _update_broker_tokens(self, broker, broker_instance):
        """Mettre à jour les tokens du broker en base de données"""
        try:
            broker.saxo_access_token = broker_instance.access_token
            broker.saxo_refresh_token = broker_instance.refresh_token
            broker.saxo_token_expires_at = broker_instance.token_expires_at
            broker.save()
            self.stdout.write("  💾 Tokens mis à jour en base de données")
        except Exception as e:
            self.stdout.write(f"  ⚠️ Erreur lors de la sauvegarde des tokens: {e}")
    
    def _log_refresh_attempt(self, broker, success, **kwargs):
        """Enregistrer une tentative de refresh en base de données"""
        try:
            TokenRefreshHistory.objects.create(
                broker_credentials=broker,
                success=success,
                new_access_token=kwargs.get('new_access_token', ''),
                new_refresh_token=kwargs.get('new_refresh_token', ''),
                expires_in_seconds=kwargs.get('expires_in', None),
                error_message=kwargs.get('error_message', ''),
                retry_count=kwargs.get('retry_count', 0),
                max_retries=5
            )
        except Exception as e:
            self.stdout.write(f"  ⚠️ Erreur lors de l'enregistrement de l'historique: {e}")
    
    def _notify_refresh_failure(self, broker, max_retries):
        """Notifier l'échec du refresh via Telegram"""
        try:
            message = f"❌ ÉCHEC REFRESH TOKEN SAXO\n\n"
            message += f"Broker: {broker.name}\n"
            message += f"Utilisateur: {broker.user.username}\n"
            message += f"Tentatives: {max_retries + 1}\n"
            message += f"Timestamp: {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
            message += f"Le refresh automatique des tokens a échoué après {max_retries + 1} tentatives.\n"
            message += f"Vérifiez la configuration du broker et la connectivité Saxo Bank."
            
            telegram_notifier.send_error_notification(message)
            self.stdout.write("  📱 Notification Telegram envoyée")
            
        except Exception as e:
            self.stdout.write(f"  ⚠️ Erreur lors de l'envoi de la notification: {e}")
    
    def _cleanup_old_history(self):
        """Nettoyer l'historique de plus de 30 jours"""
        try:
            cutoff_date = timezone.now() - timedelta(days=30)
            deleted_count = TokenRefreshHistory.objects.filter(
                refresh_attempted_at__lt=cutoff_date
            ).delete()[0]
            
            if deleted_count > 0:
                self.stdout.write(f"🧹 {deleted_count} entrées d'historique supprimées (>30 jours)")
                
        except Exception as e:
            self.stdout.write(f"⚠️ Erreur lors du nettoyage de l'historique: {e}")
