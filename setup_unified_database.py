#!/usr/bin/env python
"""
Script unifié pour configurer la base de données unique
Remplace tous les anciens scripts de migration multiples
"""

import os
import sys
import django
from pathlib import Path
import shutil

def setup_django(environment='development'):
    """Configure Django pour l'environnement spécifié"""
    settings_mapping = {
        'development': 'site_trading_v3.settings.development',
        'production_test': 'site_trading_v3.settings.production_test',
        'production': 'site_trading_v3.settings.production',
        'base': 'site_trading_v3.settings.base',
    }
    
    settings_module = settings_mapping.get(environment, 'site_trading_v3.settings.development')
    os.environ['DJANGO_SETTINGS_MODULE'] = settings_module
    
    print(f"🔧 Configuration Django: {settings_module}")
    django.setup()
    
    # Afficher quelle base de données est utilisée
    from django.conf import settings
    db_path = settings.DATABASES['default']['NAME']
    print(f"📁 Base de données: {db_path}")
    
    return db_path

def migrate_existing_data():
    """Migre les données depuis les anciennes bases vers la nouvelle base unifiée"""
    print("🔄 Migration des données existantes...")
    
    old_databases = [
        'db_test_1.sqlite3',
        'db_test_2.sqlite3', 
        'db_test_3.sqlite3',
        'db_test_4.sqlite3'
    ]
    
    # Trouver la base avec le plus de données
    best_db = None
    max_size = 0
    
    for db_file in old_databases:
        if Path(db_file).exists():
            size = Path(db_file).stat().st_size
            print(f"   📊 {db_file}: {size:,} bytes")
            if size > max_size:
                max_size = size
                best_db = db_file
    
    if best_db:
        print(f"   ✅ Base source sélectionnée: {best_db} ({max_size:,} bytes)")
        
        # Copier vers la nouvelle base unifiée
        target_db = 'trading_app.sqlite3'
        if best_db != target_db:
            shutil.copy2(best_db, target_db)
            print(f"   📋 Données copiées vers {target_db}")
        
        return True
    else:
        print("   ⚠️  Aucune base de données existante trouvée")
        return False

def run_migrations():
    """Applique toutes les migrations Django"""
    print("🗄️  Application des migrations...")
    
    try:
        from django.core.management import execute_from_command_line
        
        # Créer les migrations si nécessaire
        print("   📝 Création des migrations...")
        execute_from_command_line(['manage.py', 'makemigrations', '--verbosity=1'])
        
        # Appliquer les migrations
        print("   ⚙️  Application des migrations...")
        execute_from_command_line(['manage.py', 'migrate', '--verbosity=1'])
        
        print("   ✅ Migrations appliquées avec succès")
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur lors des migrations: {e}")
        return False

def verify_database():
    """Vérifie que la base de données fonctionne correctement"""
    print("🔍 Vérification de la base de données...")
    
    try:
        from trading_app.models import Asset, AllAssets, AssetTradable, BrokerCredentials
        
        models_to_test = [
            ('Asset', Asset),
            ('AllAssets', AllAssets),
            ('AssetTradable', AssetTradable),
            ('BrokerCredentials', BrokerCredentials),
        ]
        
        for model_name, model_class in models_to_test:
            try:
                count = model_class.objects.count()
                print(f"   ✅ {model_name}: {count} enregistrements")
            except Exception as e:
                print(f"   ❌ Erreur {model_name}: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur de vérification: {e}")
        return False

def create_superuser():
    """Crée un superutilisateur si nécessaire"""
    print("👤 Configuration du superutilisateur...")
    
    try:
        from django.contrib.auth.models import User
        
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'changeme123')
            print("   ✅ Superutilisateur créé: admin/changeme123")
            print("   ⚠️  CHANGEZ CE MOT DE PASSE DÈS QUE POSSIBLE!")
        else:
            print("   ✅ Superutilisateur existe déjà")
            
    except Exception as e:
        print(f"   ❌ Erreur superutilisateur: {e}")

def setup_environment_variables():
    """Guide pour configurer les variables d'environnement"""
    print("🔧 Configuration des variables d'environnement:")
    print()
    print("   Pour différencier les environnements, vous pouvez utiliser:")
    print()
    print("   # Développement (par défaut)")
    print("   # Aucune variable nécessaire - utilise trading_app.sqlite3")
    print()
    print("   # Test avec une base différente")
    print("   export DB_NAME=trading_app_test.sqlite3")
    print()
    print("   # Production avec une base différente") 
    print("   export DB_NAME=trading_app_prod.sqlite3")
    print()
    print("   # Ou dans un fichier .env:")
    print("   echo 'DB_NAME=trading_app.sqlite3' > .env")
    print()

def main():
    """Fonction principale"""
    print("🚀 Configuration de la base de données unifiée")
    print("=" * 60)
    
    # Vérifier le répertoire
    if not Path('manage.py').exists():
        print("❌ Erreur: manage.py non trouvé. Exécutez depuis la racine du projet.")
        sys.exit(1)
    
    # Déterminer l'environnement
    environment = 'development'
    if len(sys.argv) > 1:
        environment = sys.argv[1]
    
    # Configurer la variable d'environnement pour la base de données
    if 'DB_NAME' not in os.environ:
        os.environ['DB_NAME'] = 'trading_app.sqlite3'
    
    try:
        # 1. Configurer Django
        db_path = setup_django(environment)
        
        # 2. Migrer les données existantes si nécessaire
        if not Path(db_path).exists():
            print(f"📁 Création de la nouvelle base: {db_path}")
            migrate_existing_data()
        else:
            print(f"📁 Base de données existante: {db_path}")
        
        # 3. Appliquer les migrations
        if not run_migrations():
            print("❌ Échec des migrations")
            sys.exit(1)
        
        # 4. Vérifier la base de données
        if not verify_database():
            print("❌ Vérification échouée")
            sys.exit(1)
        
        # 5. Créer superutilisateur
        create_superuser()
        
        # 6. Guide des variables d'environnement
        setup_environment_variables()
        
        print("\n🎉 Configuration terminée avec succès !")
        print("=" * 60)
        print("📝 Prochaines étapes:")
        print(f"   1. Testez: python manage.py runserver --settings=site_trading_v3.settings.{environment}")
        print("   2. Connectez-vous à /admin/ avec admin/changeme123")
        print("   3. Changez le mot de passe admin")
        print("   4. Configurez vos credentials de broker")
        print("   5. Pour la production, définissez DB_NAME dans vos variables d'environnement")
        
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
