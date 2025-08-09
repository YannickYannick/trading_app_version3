#!/bin/bash

# Script de correction rapide pour le problème "no such table" en production
# À exécuter sur votre serveur d'hébergement

echo "🚀 Correction rapide du problème de base de données"
echo "=================================================="

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "manage.py" ]; then
    echo "❌ Erreur: manage.py non trouvé. Exécutez ce script depuis la racine du projet."
    exit 1
fi

# Activer l'environnement virtuel s'il existe
if [ -d "venv" ]; then
    echo "🔧 Activation de l'environnement virtuel..."
    source venv/bin/activate
elif [ -d "env" ]; then
    echo "🔧 Activation de l'environnement virtuel..."
    source env/bin/activate
else
    echo "⚠️  Aucun environnement virtuel détecté"
fi

# Définir les variables d'environnement pour la production
export DJANGO_SETTINGS_MODULE=site_trading_v3.settings.production

echo "📋 Variables d'environnement configurées"

# Vérifier la configuration Django
echo "🔍 Vérification de la configuration..."
python manage.py check

if [ $? -ne 0 ]; then
    echo "❌ Erreur de configuration Django. Vérifiez vos paramètres."
    exit 1
fi

# Créer les fichiers de migration si nécessaire
echo "📝 Création des migrations..."
python manage.py makemigrations

# Appliquer toutes les migrations
echo "🗄️  Application des migrations..."
python manage.py migrate --verbosity=2

if [ $? -ne 0 ]; then
    echo "❌ Erreur lors des migrations"
    exit 1
fi

# Vérifier que les tables ont été créées
echo "🔍 Vérification des tables..."
python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table';\")
tables = cursor.fetchall()
print('Tables créées:')
for table in tables:
    print(f'  - {table[0]}')
"

# Créer un superutilisateur si nécessaire
echo "👤 Configuration du superutilisateur..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'changeme123')
    print('✅ Superutilisateur créé: admin/changeme123')
    print('⚠️  CHANGEZ CE MOT DE PASSE DÈS QUE POSSIBLE!')
else:
    print('✅ Superutilisateur existe déjà')
"

# Collecter les fichiers statiques
echo "📁 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

echo ""
echo "🎉 Correction terminée !"
echo "======================="
echo "📝 Vérifications à faire:"
echo "   1. Testez l'accès à votre site"
echo "   2. Connectez-vous à /admin/ avec admin/changeme123"
echo "   3. Changez le mot de passe admin"
echo "   4. Configurez vos paramètres de broker"
echo ""
echo "🔧 Si vous avez encore des erreurs:"
echo "   1. Vérifiez les logs: tail -f logs/django.log"
echo "   2. Utilisez le script Python: python setup_database_production.py"
echo "   3. Contactez le support de votre hébergeur"
