#!/bin/bash

# Script de déploiement pour Django Trading App
echo "🚀 Démarrage du déploiement..."

# 1. Charger les variables d'environnement (optionnel)
echo "📋 Chargement des variables d'environnement..."
# Charger le fichier d'environnement s'il existe
if [ -f ".env" ]; then
    source .env
    echo "✅ Fichier .env chargé"
elif [ -f "env.production" ]; then
    source env.production
    echo "✅ Fichier env.production chargé"
else
    echo "✅ Utilisation de la base de données par défaut: db.sqlite3"
fi

# 2. Installer/updater les dépendances
echo "📦 Installation des dépendances..."
pip install -r requirements.txt

# 3. Configurer la base de données simple
echo "🗄️ Configuration de la base de données..."
python setup_simple_database.py

# 4. Collecter les fichiers statiques
echo "📁 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# 5. Le superutilisateur est créé par le script unifié

# 6. Vérifier la configuration
echo "✅ Vérification de la configuration..."
python manage.py check --deploy

echo "🎉 Déploiement terminé !"
echo "📝 N'oubliez pas de :"
echo "   - Changer le mot de passe admin"
echo "   - Configurer HTTPS"
echo "   - Configurer un serveur web (Nginx)"
echo "   - Configurer un process manager (systemd)" 