# Guide : Base de Données Unifiée

## 🎯 Nouvelle Architecture

Votre projet utilise maintenant **une seule base de données** configurable via des variables d'environnement, au lieu de 4 bases différentes.

### ✅ Avantages de cette approche :
- **Simplicité** : Une seule base à gérer
- **Flexibilité** : Configurable via variables d'environnement  
- **Cohérence** : Même structure partout
- **Déploiement facile** : Un seul script pour tout

## 📁 Configuration

### Base de données par défaut
- **Nom** : `trading_app.sqlite3`
- **Emplacement** : Racine du projet
- **Configuration** : Dans `site_trading_v3/settings/base.py`

### Variable d'environnement
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / os.environ.get('DB_NAME', 'trading_app.sqlite3'),
    }
}
```

## 🚀 Utilisation

### 1. Configuration rapide
```bash
# Utiliser la base par défaut
python setup_unified_database.py

# Ou pour un environnement spécifique
python setup_unified_database.py development
python setup_unified_database.py production_test  
python setup_unified_database.py production
```

### 2. Avec des bases différentes par environnement
```bash
# Développement avec base spécifique
export DB_NAME=trading_app_dev.sqlite3
python setup_unified_database.py development

# Test avec base spécifique
export DB_NAME=trading_app_test.sqlite3
python setup_unified_database.py production_test

# Production avec base spécifique
export DB_NAME=trading_app_prod.sqlite3
python setup_unified_database.py production
```

### 3. Avec fichier .env
```bash
# Créer un fichier .env
cp env.unified.example .env

# Éditer .env
DB_NAME=trading_app.sqlite3
DJANGO_SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,yourdomain.com

# Lancer la configuration
python setup_unified_database.py
```

## 🔧 Déploiement

### 1. Déploiement automatique
```bash
# Le script deploy.sh utilise maintenant la configuration unifiée
./deploy.sh
```

### 2. Déploiement manuel
```bash
# 1. Définir la base de données pour la production
export DB_NAME=trading_app_prod.sqlite3

# 2. Configurer la base
python setup_unified_database.py production

# 3. Collecter les fichiers statiques
python manage.py collectstatic --noinput

# 4. Vérifier la configuration
python manage.py check --deploy
```

### 3. Pour votre hébergeur
```bash
# Sur votre serveur d'hébergement
cd /chemin/vers/votre/projet

# Définir la base pour la production
export DB_NAME=trading_app_prod.sqlite3

# Ou créer un fichier .env avec:
echo "DB_NAME=trading_app_prod.sqlite3" > .env

# Lancer la configuration
python setup_unified_database.py production
```

## 🔍 Test et Vérification

### Tester chaque environnement
```bash
# Développement
python manage.py runserver --settings=site_trading_v3.settings.development

# Test de production  
export DB_NAME=trading_app_test.sqlite3
python manage.py runserver --settings=site_trading_v3.settings.production_test

# Production
export DB_NAME=trading_app_prod.sqlite3
python manage.py runserver --settings=site_trading_v3.settings.production
```

### Vérifier la base utilisée
```bash
python manage.py shell -c "
from django.conf import settings
print('Base de données:', settings.DATABASES['default']['NAME'])
"
```

### Vérifier les tables
```bash
python manage.py shell -c "
from trading_app.models import Asset, AllAssets
print('Assets:', Asset.objects.count())
print('AllAssets:', AllAssets.objects.count())
"
```

## 📋 Migration depuis l'ancienne configuration

### Migration automatique
Le script `setup_unified_database.py` migre automatiquement vos données depuis les anciennes bases (`db_test_1.sqlite3`, `db_test_2.sqlite3`, etc.) vers la nouvelle base unifiée.

### Migration manuelle
```bash
# Si vous voulez copier manuellement depuis une base spécifique
cp db_test_2.sqlite3 trading_app.sqlite3

# Puis appliquer les migrations
python setup_unified_database.py
```

## 🔧 Résolution de Problèmes

### Problème : "no such table"
```bash
# Solution : Configurer la base pour l'environnement correct
python setup_unified_database.py production
```

### Problème : Mauvaise base utilisée
```bash
# Vérifier quelle base est utilisée
python manage.py shell -c "
from django.conf import settings
print('Base actuelle:', settings.DATABASES['default']['NAME'])
"

# Définir la bonne base
export DB_NAME=trading_app_prod.sqlite3
```

### Problème : Données manquantes
```bash
# Migrer depuis une ancienne base
cp db_test_2.sqlite3 trading_app_prod.sqlite3
python setup_unified_database.py production
```

## 📝 Avantages de cette Configuration

### ✅ Pour le Développement
- Une seule base à gérer
- Configuration simple
- Pas de confusion entre environnements

### ✅ Pour la Production
- Configuration via variables d'environnement
- Facilité de déploiement
- Cohérence garantie

### ✅ Pour la Maintenance
- Scripts unifiés
- Moins de fichiers à maintenir
- Configuration centralisée

## 🎉 Résultat

Maintenant vous avez :
- **Une seule configuration de base de données** dans `base.py`
- **Un script unifié** `setup_unified_database.py` pour tous les environnements
- **Une flexibilité totale** via la variable `DB_NAME`
- **Un déploiement simplifié** avec `deploy.sh` mis à jour

Plus besoin de gérer 4 bases différentes ! 🚀
