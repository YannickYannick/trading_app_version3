import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from .models import AutomationConfig, AutomationExecutionLog, BrokerCredentials, Strategy
from .services import BrokerService
from .telegram_notifications import TelegramNotifier

logger = logging.getLogger(__name__)

class AutomationService:
    """Service d'automatisation des tâches de trading"""
    
    def __init__(self, user: User):
        self.user = user
        self.broker_service = BrokerService(user)
        self.telegram_notifier = TelegramNotifier()
        self.config = self._get_or_create_config()
    
    def _get_or_create_config(self) -> AutomationConfig:
        """Récupère ou crée la configuration d'automatisation"""
        config, created = AutomationConfig.objects.get_or_create(
            user=self.user,
            defaults={
                'is_active': False,
                'frequency_minutes': 30
            }
        )
        if created:
            logger.info(f"Configuration d'automatisation créée pour {self.user.username}")
        return config
    
    def execute_automation_cycle(self) -> dict:
        """Exécute un cycle complet d'automatisation"""
        start_time = timezone.now()
        logger.info(f"🚀 Début du cycle d'automatisation pour {self.user.username}")
        
        # Notification de début de cycle
        self.telegram_notifier.send_message(
            f"🚀 **Début Cycle d'Automatisation**\n"
            f"👤 {self.user.username}\n"
            f"⏰ {start_time.strftime('%H:%M:%S')}\n"
            f"🔄 Démarrage des synchronisations..."
        )
        
        # Initialiser les résultats
        results = {
            'summary': [],
            'api_responses': [],
            'errors': [],
            'status': 'SUCCESS'
        }
        
        try:
            # 1. Synchronisation Binance
            results.update(self._sync_binance())
            
            # 2. Synchronisation Saxo
            results.update(self._sync_saxo())
            
            # 3. Exécution des stratégies actives
            results.update(self._execute_active_strategies())
            
            # 4. Mettre à jour la configuration
            self._update_execution_time()
            
            # 5. Déterminer le statut final
            if results['errors']:
                results['status'] = 'PARTIAL' if results['summary'] else 'FAILED'
            
            # 6. Enregistrer le log
            self._save_execution_log(results, start_time)
            
            # 7. Envoyer les notifications Telegram
            self._send_telegram_notifications(results)
            
            # Notification de fin de cycle
            duration = timezone.now() - start_time
            duration_seconds = int(duration.total_seconds())
            
            self.telegram_notifier.send_message(
                f"🏁 **Fin Cycle d'Automatisation**\n"
                f"👤 {self.user.username}\n"
                f"⏱️ Durée: {duration_seconds}s\n"
                f"✅ Succès: {len(results['summary'])}\n"
                f"❌ Erreurs: {len(results['errors'])}\n"
                f"⏰ {timezone.now().strftime('%H:%M:%S')}"
            )
            
            logger.info(f"✅ Cycle d'automatisation terminé pour {self.user.username}")
            
        except Exception as e:
            error_msg = f"Erreur critique dans le cycle d'automatisation: {str(e)}"
            results['errors'].append(error_msg)
            results['status'] = 'FAILED'
            logger.error(error_msg, exc_info=True)
            
            # Enregistrer le log d'erreur
            self._save_execution_log(results, start_time)
            
            # Notifier l'erreur critique immédiatement
            self.telegram_notifier.send_error_notification(
                f"💥 **ERREUR CRITIQUE AUTOMATISATION**\n"
                f"👤 {self.user.username}\n"
                f"🔍 {error_msg}\n"
                f"⏰ {timezone.now().strftime('%H:%M:%S')}\n"
                f"🚨 Cycle interrompu !"
            )
        
        return results
    
    def _sync_binance(self) -> dict:
        """Synchronise les données Binance"""
        results = {'summary': [], 'api_responses': [], 'errors': []}
        
        try:
            # Récupérer les credentials Binance
            binance_creds = BrokerCredentials.objects.filter(
                user=self.user,
                broker_type='binance',
                is_active=True
            ).first()
            
            if not binance_creds:
                results['summary'].append("ℹ️ Aucun broker Binance actif trouvé")
                return results
            
            logger.info(f"🔄 Synchronisation Binance pour {self.user.username}")
            
            # Synchroniser les positions
            try:
                positions = self.broker_service.sync_positions_from_broker(binance_creds)
                results['summary'].append(f"✅ {len(positions)} positions Binance synchronisées")
                results['api_responses'].append(f"Positions Binance: {len(positions)} récupérées")
                
                # Notification immédiate pour les positions
                self.telegram_notifier.send_message(
                    f"🔄 **Synchronisation Binance - Positions**\n"
                    f"✅ {len(positions)} positions synchronisées\n"
                    f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                )
                
            except Exception as e:
                error_msg = f"Erreur synchronisation positions Binance: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
                
                # Notification d'erreur immédiate
                self.telegram_notifier.send_message(
                    f"❌ **Erreur Synchronisation Binance - Positions**\n"
                    f"🔍 {error_msg}\n"
                    f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                )
            
            # Synchroniser les trades
            try:
                trades_result = self.broker_service.sync_trades_from_broker(binance_creds)
                if trades_result.get('success'):
                    results['summary'].append(f"✅ {trades_result.get('count', 0)} trades Binance synchronisés")
                    results['api_responses'].append(f"Trades Binance: {trades_result.get('count', 0)} récupérés")
                    
                    # Notification immédiate pour les trades
                    self.telegram_notifier.send_message(
                        f"🔄 **Synchronisation Binance - Trades**\n"
                        f"✅ {trades_result.get('count', 0)} trades synchronisés\n"
                        f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                    )
                else:
                    results['errors'].append(f"Échec synchronisation trades Binance: {trades_result.get('error', 'Erreur inconnue')}")
                    
                    # Notification d'erreur immédiate
                    self.telegram_notifier.send_message(
                        f"❌ **Erreur Synchronisation Binance - Trades**\n"
                        f"🔍 {trades_result.get('error', 'Erreur inconnue')}\n"
                        f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                    )
            except Exception as e:
                error_msg = f"Erreur synchronisation trades Binance: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
                
                # Notification d'erreur immédiate
                self.telegram_notifier.send_message(
                    f"❌ **Erreur Synchronisation Binance - Trades**\n"
                    f"🔍 {error_msg}\n"
                    f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                )
                
        except Exception as e:
            error_msg = f"Erreur générale synchronisation Binance: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(error_msg)
        
        return results
    
    def _sync_saxo(self) -> dict:
        """Synchronise les données Saxo"""
        results = {'summary': [], 'api_responses': [], 'errors': []}
        
        try:
            # Récupérer les credentials Saxo
            saxo_creds = BrokerCredentials.objects.filter(
                user=self.user,
                broker_type='saxo',
                is_active=True
            ).first()
            
            if not saxo_creds:
                results['summary'].append("ℹ️ Aucun broker Saxo actif trouvé")
                return results
            
            logger.info(f"🔄 Synchronisation Saxo pour {self.user.username}")
            
            # Synchroniser les positions
            try:
                positions = self.broker_service.sync_positions_from_broker(saxo_creds)
                results['summary'].append(f"✅ {len(positions)} positions Saxo synchronisées")
                results['api_responses'].append(f"Positions Saxo: {len(positions)} récupérées")
                
                # Notification immédiate pour les positions
                self.telegram_notifier.send_message(
                    f"🔄 **Synchronisation Saxo - Positions**\n"
                    f"✅ {len(positions)} positions synchronisées\n"
                    f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                )
                
            except Exception as e:
                error_msg = f"Erreur synchronisation positions Saxo: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
                
                # Notification d'erreur immédiate
                self.telegram_notifier.send_message(
                    f"❌ **Erreur Synchronisation Saxo - Positions**\n"
                    f"🔍 {error_msg}\n"
                    f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                )
            
            # Synchroniser les trades
            try:
                trades_result = self.broker_service.sync_trades_from_broker(saxo_creds)
                if trades_result.get('success'):
                    results['summary'].append(f"✅ {trades_result.get('count', 0)} trades Saxo synchronisés")
                    results['summary'].append(f"✅ {trades_result.get('count', 0)} trades Saxo synchronisés")
                    results['api_responses'].append(f"Trades Saxo: {trades_result.get('count', 0)} récupérés")
                    
                    # Notification immédiate pour les trades
                    self.telegram_notifier.send_message(
                        f"🔄 **Synchronisation Saxo - Trades**\n"
                        f"✅ {trades_result.get('count', 0)} trades synchronisés\n"
                        f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                    )
                else:
                    results['errors'].append(f"Échec synchronisation trades Saxo: {trades_result.get('error', 'Erreur inconnue')}")
                    
                    # Notification d'erreur immédiate
                    self.telegram_notifier.send_error_notification(
                        f"❌ **Erreur Synchronisation Saxo - Trades**\n"
                        f"🔍 {trades_result.get('error', 'Erreur inconnue')}\n"
                        f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                    )
            except Exception as e:
                error_msg = f"Erreur synchronisation trades Saxo: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
                
                # Notification d'erreur immédiate
                self.telegram_notifier.send_error_notification(
                    f"❌ **Erreur Synchronisation Saxo - Trades**\n"
                    f"🔍 {error_msg}\n"
                    f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                )
            
            # Auto-refresh des tokens Saxo (si activé)
            if self.config.auto_refresh_tokens:
                try:
                    # Refresh systématique des tokens Saxo à chaque cycle
                    success = self.broker_service.refresh_saxo_tokens(saxo_creds)
                    if success:
                        results['summary'].append("✅ Tokens Saxo rafraîchis")
                        results['api_responses'].append("Refresh tokens Saxo: Succès")
                        
                        # Notification immédiate pour le refresh des tokens
                        self.telegram_notifier.send_message(
                            f"🔄 **Refresh Tokens Saxo**\n"
                            f"✅ Tokens rafraîchis avec succès\n"
                            f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                        )
                    else:
                        results['errors'].append("Échec du refresh des tokens Saxo")
                        
                        # Notification d'erreur immédiate
                        self.telegram_notifier.send_message(
                            f"❌ **Erreur Refresh Tokens Saxo**\n"
                            f"🔍 Échec du refresh des tokens\n"
                            f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                        )
                except Exception as e:
                    error_msg = f"Erreur refresh tokens Saxo: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
                    
                    # Notification d'erreur immédiate
                    self.telegram_notifier.send_message(
                        f"❌ **Erreur Refresh Tokens Saxo**\n"
                        f"🔍 {error_msg}\n"
                        f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                    )
            else:
                results['summary'].append("ℹ️ Refresh automatique des tokens désactivé")
                
                # Notification d'information
                self.telegram_notifier.send_message(
                    f"ℹ️ **Refresh Tokens Saxo**\n"
                    f"📋 Refresh automatique désactivé par l'utilisateur\n"
                    f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                )
                
        except Exception as e:
            error_msg = f"Erreur générale synchronisation Saxo: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(error_msg)
        
        return results
    
    def _execute_active_strategies(self) -> dict:
        """Exécute les stratégies actives"""
        results = {'summary': [], 'api_responses': [], 'errors': []}
        
        try:
            # Récupérer les stratégies actives (status = 'ACTIVE')
            active_strategies = Strategy.objects.filter(
                user=self.user,
                status='ACTIVE'
            )
            
            if not active_strategies.exists():
                results['summary'].append("ℹ️ Aucune stratégie active trouvée")
                return results
            
            logger.info(f"🚀 Exécution de {active_strategies.count()} stratégies actives pour {self.user.username}")
            
            executed_count = 0
            for strategy in active_strategies:
                try:
                    # Exécuter la stratégie
                    from .views import execute_strategy
                    result = execute_strategy(strategy.id)
                    
                    if result.get('success'):
                        executed_count += 1
                        results['summary'].append(f"✅ Stratégie {strategy.name} exécutée")
                        results['api_responses'].append(f"Stratégie {strategy.name}: {result.get('message', 'Succès')}")
                        
                        # Notification immédiate pour l'exécution réussie
                        self.telegram_notifier.send_message(
                            f"🚀 **Exécution Stratégie**\n"
                            f"✅ {strategy.name} exécutée avec succès\n"
                            f"📊 {result.get('message', 'Succès')}\n"
                            f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                        )
                    else:
                        results['errors'].append(f"Échec exécution stratégie {strategy.name}: {result.get('error', 'Erreur inconnue')}")
                        
                        # Notification d'erreur immédiate
                        self.telegram_notifier.send_error_notification(
                            f"❌ **Erreur Exécution Stratégie**\n"
                            f"🔍 {strategy.name}: {result.get('error', 'Erreur inconnue')}\n"
                            f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                        )
                        
                except Exception as e:
                    error_msg = f"Erreur exécution stratégie {strategy.name}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
                    
                    # Notification d'erreur immédiate
                    self.telegram_notifier.send_error_notification(
                        f"❌ **Erreur Critique Exécution Stratégie**\n"
                        f"🔍 {strategy.name}: {error_msg}\n"
                        f"⏰ {timezone.now().strftime('%H:%M:%S')}"
                    )
                    continue  # Continuer avec les autres stratégies
            
            if executed_count > 0:
                results['summary'].append(f"✅ {executed_count}/{active_strategies.count()} stratégies exécutées avec succès")
            else:
                results['summary'].append("⚠️ Aucune stratégie n'a pu être exécutée")
                
        except Exception as e:
            error_msg = f"Erreur générale exécution stratégies: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(error_msg)
        
        return results
    
    def _update_execution_time(self):
        """Met à jour les temps d'exécution"""
        now = timezone.now()
        self.config.last_execution = now
        self.config.next_execution = self.config.calculate_next_execution()
        self.config.save()
    
    def _save_execution_log(self, results: dict, start_time: datetime):
        """Sauvegarde le log d'exécution"""
        try:
            execution_duration = timezone.now() - start_time
            
            AutomationExecutionLog.objects.create(
                user=self.user,
                status=results['status'],
                summary='\n'.join(results['summary']) if results['summary'] else 'Aucune action effectuée',
                api_responses='\n'.join(results['api_responses']) if results['api_responses'] else 'Aucune réponse API',
                errors='\n'.join(results['errors']) if results['errors'] else '',
                execution_duration=execution_duration
            )
            
            logger.info(f"Log d'exécution sauvegardé pour {self.user.username}")
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde log d'exécution: {str(e)}")
    
    def _send_telegram_notifications(self, results: dict):
        """Envoie les notifications Telegram"""
        try:
            # Message 1: Résumé des actions
            if results['summary']:
                summary_msg = "🔄 **Résumé de l'Automatisation**\n\n" + '\n'.join(results['summary'])
                self.telegram_notifier.send_message(summary_msg)
            
            # Message 2: Réponses des APIs
            if results['api_responses']:
                api_msg = "📊 **Réponses des APIs**\n\n" + '\n'.join(results['api_responses'])
                self.telegram_notifier.send_message(api_msg)
            
            # Message 3: Erreurs
            if results['errors']:
                error_msg = "❌ **Erreurs Rencontrées**\n\n" + '\n'.join(results['errors'])
                self.telegram_notifier.send_error_notification(error_msg)
            
            logger.info(f"Notifications Telegram envoyées pour {self.user.username}")
            
        except Exception as e:
            logger.error(f"Erreur envoi notifications Telegram: {str(e)}")
    
    def start_automation(self):
        """Démarre l'automatisation"""
        self.config.is_active = True
        self.config.save()
        logger.info(f"Automatisation démarrée pour {self.user.username}")
    
    def stop_automation(self):
        """Arrête l'automatisation"""
        self.config.is_active = False
        self.config.save()
        logger.info(f"Automatisation arrêtée pour {self.user.username}")
    
    def pause_automation(self):
        """Met en pause l'automatisation"""
        self.config.is_active = False
        self.config.save()
        logger.info(f"Automatisation mise en pause pour {self.user.username}")
    
    def resume_automation(self):
        """Reprend l'automatisation"""
        self.config.is_active = True
        self.config.save()
        logger.info(f"Automatisation reprise pour {self.user.username}")
    
    def update_frequency(self, frequency_minutes: int):
        """Met à jour la fréquence d'exécution"""
        self.config.frequency_minutes = frequency_minutes
        self.config.save()
        logger.info(f"Fréquence d'automatisation mise à jour: {frequency_minutes} minutes pour {self.user.username}")
    
    def toggle_auto_refresh_tokens(self, enabled: bool):
        """Active/désactive le refresh automatique des tokens"""
        self.config.auto_refresh_tokens = enabled
        self.config.save()
        status = "activé" if enabled else "désactivé"
        logger.info(f"Refresh automatique des tokens {status} pour {self.user.username}")
    
    def get_status(self) -> dict:
        """Retourne le statut de l'automatisation"""
        return {
            'is_active': self.config.is_active,
            'frequency_minutes': self.config.frequency_minutes,
            'auto_refresh_tokens': self.config.auto_refresh_tokens,
            'last_execution': self.config.last_execution,
            'next_execution': self.config.next_execution,
            'created_at': self.config.created_at,
            'updated_at': self.config.updated_at
        }
    

