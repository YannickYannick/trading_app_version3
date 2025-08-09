#!/usr/bin/env python
"""
Script simple pour configurer la base de données unique db.sqlite3
Version simplifiée sans variables d'environnement
"""

import os
import sys
import django
from pathlib import Path
import shutil

def setup_django():
    """Configure Django avec les paramètres de développement par défaut"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings.development')
    django.setup()
    print("🔧 Django configuré")

def migrate_existing_data():
    """Migre les données depuis les anciennes bases vers db.sqlite3"""
    print("🔄 Migration des données existantes...")
    
    # Chercher la base avec le plus de données
    old_databases = [
        'db_test_1.sqlite3',
        'db_test_2.sqlite3', 
        'db_test_3.sqlite3',
        'db_test_4.sqlite3',
        'trading_app.sqlite3'
    ]
    
    best_db = None
    max_size = 0
    
    for db_file in old_databases:
        if Path(db_file).exists():
            size = Path(db_file).stat().st_size
            print(f"   📊 {db_file}: {size:,} bytes")
            if size > max_size:
                max_size = size
                best_db = db_file
    
    target_db = 'db.sqlite3'
    
    if best_db and best_db != target_db:
        print(f"   ✅ Migration depuis: {best_db} ({max_size:,} bytes)")
        shutil.copy2(best_db, target_db)
        print(f"   📋 Données copiées vers {target_db}")
        return True
    elif Path(target_db).exists():
        print(f"   ✅ Base de données {target_db} existe déjà")
        return True
    else:
        print("   📁 Création d'une nouvelle base de données")
        return False

def run_migrations():
    """Applique toutes les migrations Django"""
    print("🗄️  Application des migrations...")
    
    try:
        from django.core.management import execute_from_command_line
        
        # Créer les migrations si nécessaire
        print("   📝 Vérification des migrations...")
        execute_from_command_line(['manage.py', 'makemigrations', '--verbosity=0'])
        
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
        
        print("   ✅ Toutes les tables sont accessibles")
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

def cleanup_old_databases():
    """Propose de nettoyer les anciennes bases de données"""
    print("🧹 Nettoyage des anciennes bases de données...")
    
    old_databases = [
        'db_test_1.sqlite3',
        'db_test_2.sqlite3', 
        'db_test_3.sqlite3',
        'db_test_4.sqlite3',
        'trading_app.sqlite3'
    ]
    
    found_old = []
    for db_file in old_databases:
        if Path(db_file).exists():
            found_old.append(db_file)
    
    if found_old:
        print(f"   📁 Anciennes bases trouvées: {', '.join(found_old)}")
        print("   💡 Vous pouvez les supprimer maintenant que vous utilisez db.sqlite3")
        print("   🗑️  Pour les supprimer: rm " + ' '.join(found_old))
    else:
        print("   ✅ Aucune ancienne base de données trouvée")

def main():
    """Fonction principale"""
    print("🚀 Configuration de la base de données simple: db.sqlite3")
    print("=" * 60)
    
    # Vérifier le répertoire
    if not Path('manage.py').exists():
        print("❌ Erreur: manage.py non trouvé. Exécutez depuis la racine du projet.")
        sys.exit(1)
    
    try:
        # 1. Configurer Django
        setup_django()
        
        # 2. Migrer les données existantes si nécessaire
        migrate_existing_data()
        
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
        
        # 6. Proposer le nettoyage
        cleanup_old_databases()
        
        print("\n🎉 Configuration terminée avec succès !")
        print("=" * 60)
        print("📁 Base de données: db.sqlite3")
        print("📝 Prochaines étapes:")
        print("   1. Testez: python manage.py runserver")
        print("   2. Connectez-vous à /admin/ avec admin/changeme123")
        print("   3. Changez le mot de passe admin")
        print("   4. Testez votre URL: /assets/tabulator/")
        print("   5. Déployez avec: ./deploy.sh")
        
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
