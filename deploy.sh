#!/bin/bash

# Script de déploiement pour Django Trading App
echo "🚀 Démarrage du déploiement..."

# 1. Charger les variables d'environnement
echo "📋 Chargement des variables d'environnement..."
source env.production

# 2. Installer/updater les dépendances
echo "📦 Installation des dépendances..."
pip install -r requirements.txt

# 3. Appliquer les migrations
echo "🗄️ Application des migrations..."
python manage.py migrate

# 4. Collecter les fichiers statiques
echo "📁 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# 5. Créer un superutilisateur si nécessaire
echo "👤 Vérification du superutilisateur..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'changeme123')
    print('Superutilisateur créé: admin/changeme123')
else:
    print('Superutilisateur existe déjà')
"

# 6. Vérifier la configuration
echo "✅ Vérification de la configuration..."
python manage.py check --deploy

echo "🎉 Déploiement terminé !"
echo "📝 N'oubliez pas de :"
echo "   - Changer le mot de passe admin"
echo "   - Configurer HTTPS"
echo "   - Configurer un serveur web (Nginx)"
echo "   - Configurer un process manager (systemd)" 