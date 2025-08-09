#!/usr/bin/env python
"""
Script de configuration de la base de données pour la production
Résout le problème "no such table" en appliquant toutes les migrations nécessaires
"""

import os
import sys
import django
from pathlib import Path

def setup_django(settings_module=None):
    """Configure Django pour utiliser les paramètres spécifiés"""
    # Définir le module de paramètres
    if settings_module:
        os.environ['DJANGO_SETTINGS_MODULE'] = settings_module
    else:
        # Détecter automatiquement l'environnement
        if 'production_test' in sys.argv or '--production-test' in sys.argv:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings.production_test')
            print("🔧 Mode: Production Test (db_test_3.sqlite3)")
        else:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings.production')
            print("🔧 Mode: Production (db_test_4.sqlite3)")
    
    # Configurer Django
    django.setup()

def run_migrations():
    """Applique toutes les migrations Django"""
    print("🗄️  Application des migrations Django...")
    
    from django.core.management import execute_from_command_line
    
    # Liste des applications avec leurs migrations
    apps_to_migrate = [
        'auth',           # Django auth system
        'contenttypes',   # Django content types
        'sessions',       # Django sessions
        'admin',          # Django admin
        'trading_app',    # Notre app principale
        'bachata_app',    # App bachata
        'cocktails_app',  # App cocktails
        'cocktails_v2_app', # App cocktails v2
    ]
    
    try:
        # Appliquer les migrations pour chaque app
        for app in apps_to_migrate:
            print(f"   📋 Migration de {app}...")
            try:
                execute_from_command_line(['manage.py', 'migrate', app])
            except Exception as e:
                print(f"   ⚠️  Erreur lors de la migration de {app}: {e}")
                # Continuer avec les autres apps
        
        # Migration générale pour tout ce qui reste
        print("   📋 Migration générale...")
        execute_from_command_line(['manage.py', 'migrate'])
        
        print("✅ Toutes les migrations ont été appliquées avec succès !")
        
    except Exception as e:
        print(f"❌ Erreur lors des migrations: {e}")
        return False
    
    return True

def create_superuser():
    """Crée un superutilisateur si nécessaire"""
    print("👤 Vérification du superutilisateur...")
    
    try:
        from django.contrib.auth.models import User
        
        if not User.objects.filter(is_superuser=True).exists():
            # Créer un superutilisateur par défaut
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='changeme123'
            )
            print("✅ Superutilisateur créé: admin/changeme123")
            print("⚠️  IMPORTANT: Changez ce mot de passe dès que possible !")
        else:
            print("✅ Superutilisateur existe déjà")
            
    except Exception as e:
        print(f"❌ Erreur lors de la création du superutilisateur: {e}")

def verify_database():
    """Vérifie que les tables ont été créées correctement"""
    print("🔍 Vérification de la base de données...")
    
    try:
        from trading_app.models import Asset, AllAssets, AssetTradable, BrokerCredentials
        
        # Tester l'accès aux modèles principaux
        models_to_test = [
            ('Asset', Asset),
            ('AllAssets', AllAssets),
            ('AssetTradable', AssetTradable),
            ('BrokerCredentials', BrokerCredentials),
        ]
        
        for model_name, model_class in models_to_test:
            try:
                count = model_class.objects.count()
                print(f"   ✅ Table {model_name}: {count} enregistrements")
            except Exception as e:
                print(f"   ❌ Erreur avec la table {model_name}: {e}")
                return False
        
        print("✅ Toutes les tables sont accessibles !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False

def main():
    """Fonction principale"""
    print("🚀 Configuration de la base de données pour la production")
    print("=" * 60)
    
    # Vérifier que nous sommes dans le bon répertoire
    if not Path('manage.py').exists():
        print("❌ Erreur: manage.py non trouvé. Exécutez ce script depuis la racine du projet.")
        sys.exit(1)
    
    try:
        # 1. Configurer Django
        print("⚙️  Configuration de Django...")
        setup_django()
        print("✅ Django configuré")
        
        # 2. Appliquer les migrations
        if not run_migrations():
            print("❌ Échec des migrations")
            sys.exit(1)
        
        # 3. Créer un superutilisateur si nécessaire
        create_superuser()
        
        # 4. Vérifier la base de données
        if not verify_database():
            print("❌ Vérification de la base de données échouée")
            sys.exit(1)
        
        print("\n🎉 Configuration terminée avec succès !")
        print("=" * 60)
        print("📝 Prochaines étapes:")
        print("   1. Connectez-vous à l'admin Django (/admin/)")
        print("   2. Changez le mot de passe admin")
        print("   3. Configurez vos credentials de broker")
        print("   4. Importez vos données d'assets si nécessaire")
        
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
