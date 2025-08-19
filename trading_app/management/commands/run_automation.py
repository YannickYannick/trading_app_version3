from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from trading_app.models import AutomationConfig
from trading_app.automation_service import AutomationService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Exécute le cycle d\'automatisation pour tous les utilisateurs actifs'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Nom d\'utilisateur spécifique pour exécuter l\'automatisation'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forcer l\'exécution même si l\'automatisation est inactive'
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        self.stdout.write(f"🚀 Début de l'exécution de l'automatisation à {start_time}")
        
        # Récupérer les utilisateurs à traiter
        if options['user']:
            try:
                users = [User.objects.get(username=options['user'])]
                self.stdout.write(f"👤 Exécution pour l'utilisateur: {options['user']}")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ Utilisateur {options['user']} non trouvé"))
                return
        else:
            # Tous les utilisateurs avec automatisation active
            active_configs = AutomationConfig.objects.filter(is_active=True)
            users = [config.user for config in active_configs]
            self.stdout.write(f"👥 {len(users)} utilisateurs avec automatisation active trouvés")
        
        if not users:
            self.stdout.write(self.style.WARNING("⚠️ Aucun utilisateur à traiter"))
            return
        
        # Exécuter l'automatisation pour chaque utilisateur
        success_count = 0
        error_count = 0
        
        for user in users:
            try:
                self.stdout.write(f"🔄 Traitement de l'utilisateur: {user.username}")
                
                # Vérifier si l'automatisation est active (sauf si --force)
                if not options['force']:
                    config = AutomationConfig.objects.filter(user=user).first()
                    if not config or not config.is_active:
                        self.stdout.write(f"⏭️ Automatisation inactive pour {user.username}, ignoré")
                        continue
                
                # Exécuter le cycle d'automatisation
                automation_service = AutomationService(user)
                results = automation_service.execute_automation_cycle()
                
                # Afficher les résultats
                status_emoji = "✅" if results['status'] == 'SUCCESS' else "⚠️" if results['status'] == 'PARTIAL' else "❌"
                self.stdout.write(f"{status_emoji} {user.username}: {results['status']}")
                
                if results['summary']:
                    for summary in results['summary']:
                        self.stdout.write(f"   {summary}")
                
                if results['errors']:
                    for error in results['errors']:
                        self.stdout.write(self.style.ERROR(f"   ❌ {error}"))
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"❌ Erreur pour {user.username}: {str(e)}"))
                logger.error(f"Erreur automatisation pour {user.username}: {str(e)}", exc_info=True)
                continue
        
        # Résumé final
        end_time = timezone.now()
        duration = end_time - start_time
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write(f"📊 RÉSUMÉ DE L'EXÉCUTION")
        self.stdout.write(f"⏱️  Durée totale: {duration}")
        self.stdout.write(f"✅ Succès: {success_count}")
        self.stdout.write(f"❌ Erreurs: {error_count}")
        self.stdout.write(f"👥 Utilisateurs traités: {len(users)}")
        self.stdout.write("="*50)
        
        if error_count == 0:
            self.stdout.write(self.style.SUCCESS("🎉 Toutes les automatisations ont été exécutées avec succès !"))
        elif success_count > 0:
            self.stdout.write(self.style.WARNING("⚠️ Certaines automatisations ont échoué"))
        else:
            self.stdout.write(self.style.ERROR("❌ Toutes les automatisations ont échoué"))
