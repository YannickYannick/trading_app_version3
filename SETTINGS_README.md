# Configuration des Environnements Django

Ce projet utilise une configuration modulaire pour gérer différents environnements (développement et production).

## Structure des Fichiers

```
site_trading_v3/
├── settings/
│   ├── __init__.py
│   ├── base.py          # Configuration de base (commune)
│   ├── development.py   # Configuration pour le développement
│   └── production.py    # Configuration pour la production
├── manage.py            # Utilise development.py par défaut
├── run_production.py    # Script pour exécuter en production
└── env.example          # Exemple de variables d'environnement
```

## Utilisation

### Développement (par défaut)

```bash
# Utilise automatiquement development.py
python manage.py runserver
python manage.py migrate
python manage.py createsuperuser
```

### Production

#### Option 1: Utiliser le script dédié
```bash
python run_production.py runserver
python run_production.py migrate
python run_production.py collectstatic
```

#### Option 2: Définir la variable d'environnement
```bash
# Windows
set DJANGO_SETTINGS_MODULE=site_trading_v3.settings.production
python manage.py runserver

# Linux/Mac
export DJANGO_SETTINGS_MODULE=site_trading_v3.settings.production
python manage.py runserver
```

## Configuration de Production

### 1. Variables d'Environnement

Créez un fichier `.env` basé sur `env.example` :

```bash
cp env.example .env
```

Modifiez le fichier `.env` avec vos vraies valeurs :

```env
DJANGO_SECRET_KEY=votre-cle-secrete-super-securisee
DB_NAME=trading_app
DB_USER=postgres
DB_PASSWORD=votre-mot-de-passe
DB_HOST=localhost
DB_PORT=5432
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com
```

### 2. Installation des Dépendances

Pour la production, vous aurez besoin de packages supplémentaires :

```bash
pip install psycopg2-binary  # Pour PostgreSQL
pip install redis            # Pour le cache Redis
pip install python-dotenv    # Pour charger les variables d'environnement
```

### 3. Base de Données

La configuration de production utilise PostgreSQL. Assurez-vous d'avoir :

1. PostgreSQL installé et configuré
2. Une base de données créée
3. Un utilisateur avec les permissions appropriées

### 4. Cache Redis (Recommandé)

Pour de meilleures performances en production :

```bash
# Installer Redis
# Sur Ubuntu/Debian
sudo apt-get install redis-server

# Sur Windows, utiliser WSL ou Docker
docker run -d -p 6379:6379 redis:alpine
```

## Différences entre les Environnements

### Développement
- `DEBUG = True`
- Base de données SQLite
- Logs dans la console
- Cache en mémoire
- Pas de sécurité HTTPS
- CORS ouvert

### Production
- `DEBUG = False`
- Base de données PostgreSQL
- Logs dans des fichiers
- Cache Redis
- Sécurité HTTPS activée
- CORS restreint
- Variables d'environnement pour les secrets

## Sécurité

⚠️ **Important** : En production, assurez-vous de :

1. Changer la clé secrète Django
2. Configurer une base de données sécurisée
3. Utiliser HTTPS
4. Configurer correctement les hôtes autorisés
5. Ne jamais commiter le fichier `.env` dans Git

## Déploiement

Pour déployer en production :

1. Configurer les variables d'environnement
2. Installer les dépendances de production
3. Configurer la base de données PostgreSQL
4. Configurer Redis (optionnel mais recommandé)
5. Exécuter les migrations
6. Collecter les fichiers statiques
7. Configurer un serveur web (Nginx + Gunicorn recommandé) 