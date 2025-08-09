#!/usr/bin/env python
"""
Script pour vérifier rapidement l'état de tous les environnements
"""

import os
import sys
import django
from pathlib import Path

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

def check_database_tables(db_path):
    """Vérifie les tables dans une base de données SQLite"""
    if not Path(db_path).exists():
        return "❌ Fichier n'existe pas"
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Compter toutes les tables
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        total_tables = cursor.fetchone()[0]
        
        # Compter les tables trading_app
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE 'trading_app_%';")
        trading_tables = cursor.fetchone()[0]
        
        # Lister les tables trading_app
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'trading_app_%' ORDER BY name;")
        table_names = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        if trading_tables > 0:
            return f"✅ {total_tables} tables total, {trading_tables} trading_app: {', '.join(table_names)}"
        else:
            return f"⚠️  {total_tables} tables total, 0 trading_app"
            
    except Exception as e:
        return f"❌ Erreur: {e}"

def check_environment_config(env_name, config):
    """Vérifie la configuration d'un environnement"""
    try:
        # Sauvegarder l'ancienne config
        old_settings = os.environ.get('DJANGO_SETTINGS_MODULE')
        
        # Configurer Django
        os.environ['DJANGO_SETTINGS_MODULE'] = config['settings']
        
        # Recharger Django si nécessaire
        if 'django.conf' in sys.modules:
            from django.conf import settings
            if settings.configured:
                from importlib import reload
                import django.conf
                reload(django.conf)
        
        django.setup()
        
        from django.conf import settings
        
        # Vérifier la configuration de base de données
        db_config = settings.DATABASES['default']
        db_path = str(db_config['NAME'])
        
        # Restaurer l'ancienne config
        if old_settings:
            os.environ['DJANGO_SETTINGS_MODULE'] = old_settings
        
        return {
            'engine': db_config['ENGINE'],
            'db_path': db_path,
            'debug': getattr(settings, 'DEBUG', False),
            'allowed_hosts': getattr(settings, 'ALLOWED_HOSTS', [])
        }
        
    except Exception as e:
        return f"❌ Erreur config: {e}"

def main():
    """Fonction principale"""
    print("🔍 Vérification de tous les environnements Django")
    print("=" * 80)
    
    if not Path('manage.py').exists():
        print("❌ Erreur: manage.py non trouvé. Exécutez depuis la racine du projet.")
        sys.exit(1)
    
    print(f"{'Environnement':<15} {'Base de données':<20} {'État des tables'}")
    print("-" * 80)
    
    for env_name, config in ENVIRONMENTS.items():
        db_file = config['db_file']
        db_status = check_database_tables(db_file)
        
        print(f"{env_name:<15} {db_file:<20} {db_status}")
        
        # Vérifier la configuration Django
        django_config = check_environment_config(env_name, config)
        if isinstance(django_config, dict):
            print(f"{'':15} {'':20} 🔧 DEBUG={django_config['debug']}, HOSTS={django_config['allowed_hosts']}")
        else:
            print(f"{'':15} {'':20} {django_config}")
        
        print()
    
    print("=" * 80)
    print("📋 Résumé:")
    
    # Compter les bases avec des données
    working_dbs = 0
    for env_name, config in ENVIRONMENTS.items():
        db_status = check_database_tables(config['db_file'])
        if '✅' in db_status:
            working_dbs += 1
    
    print(f"   • {working_dbs}/4 bases de données contiennent des tables trading_app")
    
    if working_dbs == 0:
        print("   ⚠️  Aucune base de données n'a de tables - exécutez sync_all_databases.py")
    elif working_dbs < 4:
        print("   ⚠️  Certaines bases sont incomplètes - exécutez sync_all_databases.py")
    else:
        print("   ✅ Toutes les bases de données sont synchronisées")
    
    print("\n🚀 Commandes pour tester chaque environnement:")
    for env_name, config in ENVIRONMENTS.items():
        print(f"   python manage.py runserver --settings={config['settings']}")

if __name__ == "__main__":
    main()
