#!/usr/bin/env python
"""
Script pour synchroniser toutes les bases de données de tous les environnements
Résout le problème des multiples bases de données (db_test_1, db_test_2, db_test_3, db_test_4)
"""

import os
import sys
import django
from pathlib import Path
import shutil

# Configuration des environnements
ENVIRONMENTS = {
    'base': {
        'settings': 'site_trading_v3.settings',
        'db_file': 'db_test_1.sqlite3',
        'description': 'Configuration de base'
    },
    'development': {
        'settings': 'site_trading_v3.settings.development',
        'db_file': 'db_test_2.sqlite3',
        'description': 'Développement local'
    },
    'production_test': {
        'settings': 'site_trading_v3.settings.production_test',
        'db_file': 'db_test_3.sqlite3',
        'description': 'Test de production'
    },
    'production': {
        'settings': 'site_trading_v3.settings.production',
        'db_file': 'db_test_4.sqlite3',
        'description': 'Production'
    }
}

def setup_django(settings_module):
    """Configure Django avec un module de paramètres spécifique"""
    os.environ['DJANGO_SETTINGS_MODULE'] = settings_module
    django.setup()

def check_database_exists(db_path):
    """Vérifie si une base de données existe et contient des tables"""
    if not Path(db_path).exists():
        return False, "Fichier n'existe pas"
    
    try:
        # Configurer temporairement Django pour vérifier les tables
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'trading_app_%';")
        tables = cursor.fetchall()
        
        if tables:
            return True, f"{len(tables)} tables trading_app trouvées"
        else:
            return False, "Aucune table trading_app"
    except Exception as e:
        return False, f"Erreur: {e}"

def apply_migrations(env_name, settings_module):
    """Applique les migrations pour un environnement spécifique"""
    print(f"🔧 Configuration de {env_name}...")
    
    # Configurer Django
    setup_django(settings_module)
    
    try:
        from django.core.management import execute_from_command_line
        
        # Créer les migrations si nécessaire
        print(f"   📝 Création des migrations pour {env_name}...")
        execute_from_command_line(['manage.py', 'makemigrations', '--verbosity=0'])
        
        # Appliquer les migrations
        print(f"   🗄️  Application des migrations pour {env_name}...")
        execute_from_command_line(['manage.py', 'migrate', '--verbosity=1'])
        
        # Vérifier les tables créées
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'trading_app_%';")
        tables = cursor.fetchall()
        
        print(f"   ✅ {env_name}: {len(tables)} tables trading_app créées")
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur pour {env_name}: {e}")
        return False

def copy_database_content(source_db, target_db):
    """Copie le contenu d'une base de données vers une autre"""
    try:
        if Path(source_db).exists() and Path(target_db).exists():
            # Sauvegarde de la cible
            backup_path = f"{target_db}.backup"
            shutil.copy2(target_db, backup_path)
            print(f"   💾 Sauvegarde créée: {backup_path}")
            
            # Copie du contenu (structure + données)
            shutil.copy2(source_db, target_db)
            print(f"   📋 Contenu copié de {source_db} vers {target_db}")
            return True
    except Exception as e:
        print(f"   ❌ Erreur de copie: {e}")
        return False

def create_superuser_for_env(env_name, settings_module):
    """Crée un superutilisateur pour un environnement"""
    try:
        setup_django(settings_module)
        from django.contrib.auth.models import User
        
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'changeme123')
            print(f"   👤 Superutilisateur créé pour {env_name}: admin/changeme123")
        else:
            print(f"   ✅ Superutilisateur existe déjà pour {env_name}")
    except Exception as e:
        print(f"   ⚠️  Erreur superutilisateur {env_name}: {e}")

def main():
    """Fonction principale"""
    print("🚀 Synchronisation de toutes les bases de données")
    print("=" * 60)
    
    # Vérifier le répertoire
    if not Path('manage.py').exists():
        print("❌ Erreur: manage.py non trouvé. Exécutez depuis la racine du projet.")
        sys.exit(1)
    
    # 1. État initial des bases de données
    print("📊 État initial des bases de données:")
    db_states = {}
    for env_name, config in ENVIRONMENTS.items():
        db_path = config['db_file']
        exists, status = check_database_exists(db_path)
        db_states[env_name] = {'exists': exists, 'status': status, 'path': db_path}
        print(f"   {env_name:15} ({db_path:20}): {status}")
    
    print("\n" + "=" * 60)
    
    # 2. Identifier la base de données source (celle qui a des données)
    source_env = None
    for env_name, state in db_states.items():
        if state['exists'] and 'tables' in state['status']:
            source_env = env_name
            print(f"📋 Base de données source détectée: {env_name} ({state['path']})")
            break
    
    if not source_env:
        print("⚠️  Aucune base de données avec des tables détectée.")
        print("🔧 Application des migrations à tous les environnements...")
        
        # Appliquer les migrations à tous les environnements
        for env_name, config in ENVIRONMENTS.items():
            success = apply_migrations(env_name, config['settings'])
            if success:
                create_superuser_for_env(env_name, config['settings'])
    else:
        print(f"\n🔄 Synchronisation depuis {source_env}...")
        source_path = db_states[source_env]['path']
        
        # Copier la base source vers les autres environnements
        for env_name, config in ENVIRONMENTS.items():
            if env_name != source_env:
                target_path = config['db_file']
                print(f"\n📋 Synchronisation {env_name}:")
                
                # Appliquer d'abord les migrations pour créer la structure
                apply_migrations(env_name, config['settings'])
                
                # Puis copier les données si nécessaire
                if Path(source_path).exists():
                    copy_database_content(source_path, target_path)
                
                # Créer superutilisateur
                create_superuser_for_env(env_name, config['settings'])
    
    # 3. Vérification finale
    print("\n" + "=" * 60)
    print("🔍 Vérification finale:")
    for env_name, config in ENVIRONMENTS.items():
        db_path = config['db_file']
        # Réinitialiser Django pour chaque vérification
        if 'django' in sys.modules:
            from importlib import reload
            reload(sys.modules['django'])
        
        try:
            setup_django(config['settings'])
            exists, status = check_database_exists(db_path)
            print(f"   {env_name:15} ({db_path:20}): {status}")
        except Exception as e:
            print(f"   {env_name:15} ({db_path:20}): Erreur - {e}")
    
    print("\n🎉 Synchronisation terminée !")
    print("=" * 60)
    print("📝 Prochaines étapes:")
    print("   1. Testez chaque environnement:")
    print("      - python manage.py runserver --settings=site_trading_v3.settings.development")
    print("      - python manage.py runserver --settings=site_trading_v3.settings.production_test")
    print("   2. Déployez avec la bonne configuration sur votre hébergeur")
    print("   3. Changez les mots de passe admin sur tous les environnements")

if __name__ == "__main__":
    main()
