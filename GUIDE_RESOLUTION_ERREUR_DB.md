# Guide de Résolution : Erreur "no such table"

## 🔍 Le Problème

L'erreur `OperationalError: no such table: trading_app_asset` indique que les tables de votre base de données n'ont pas été créées sur votre serveur d'hébergement.

**Pourquoi ça marche en local mais pas en production ?**
- En local : Vous avez exécuté `python manage.py migrate`
- En production : Les migrations n'ont pas été appliquées

## ⚡ Solution Rapide

### Option 1: Script Automatique (Recommandé)

```bash
# 1. Connectez-vous à votre serveur via SSH
ssh votre_utilisateur@votre_serveur

# 2. Naviguez vers votre projet
cd /chemin/vers/votre/projet

# 3. Exécutez le script de correction
bash quick_fix_production.sh
```

### Option 2: Script Python Avancé

```bash
# Si le script bash ne fonctionne pas, utilisez le script Python
python setup_database_production.py
```

### Option 3: Commandes Manuelles

```bash
# 1. Activer l'environnement virtuel
source venv/bin/activate  # ou source env/bin/activate

# 2. Configurer Django pour la production
export DJANGO_SETTINGS_MODULE=site_trading_v3.settings.production

# 3. Créer les migrations si nécessaire
python manage.py makemigrations

# 4. Appliquer toutes les migrations
python manage.py migrate

# 5. Vérifier que ça fonctionne
python manage.py shell -c "from trading_app.models import Asset; print('Tables créées!')"

# 6. Créer un superutilisateur
python manage.py createsuperuser

# 7. Collecter les fichiers statiques
python manage.py collectstatic --noinput
```

## 🔧 Diagnostic Avancé

### Vérifier les Tables Existantes

```bash
# Pour SQLite
python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table';\")
tables = cursor.fetchall()
print('Tables existantes:')
for table in tables:
    print(f'  - {table[0]}')
"
```

### Vérifier les Migrations

```bash
# Voir l'état des migrations
python manage.py showmigrations

# Appliquer une migration spécifique
python manage.py migrate trading_app 0001
```

### Vérifier la Configuration

```bash
# Tester la configuration Django
python manage.py check --deploy

# Vérifier les paramètres de base de données
python manage.py shell -c "
from django.conf import settings
print('Base de données:', settings.DATABASES['default'])
"
```

## 🚨 Problèmes Courants et Solutions

### 1. "Permission denied"
```bash
# Donner les bonnes permissions
chmod +x quick_fix_production.sh
sudo chown -R votre_utilisateur:votre_groupe /chemin/vers/projet
```

### 2. "Module not found"
```bash
# Vérifier l'environnement virtuel
which python
pip list | grep Django

# Réinstaller les dépendances
pip install -r requirements.txt
```

### 3. "Database is locked"
```bash
# Arrêter les processus Django
pkill -f "python.*manage.py"
pkill -f gunicorn

# Redémarrer
python manage.py migrate
```

### 4. "ALLOWED_HOSTS error"
```bash
# Vérifier les paramètres de production
python manage.py shell -c "
from django.conf import settings
print('ALLOWED_HOSTS:', settings.ALLOWED_HOSTS)
"
```

## 📋 Checklist de Vérification

Après avoir appliqué la solution, vérifiez :

- [ ] ✅ Les migrations sont appliquées : `python manage.py showmigrations`
- [ ] ✅ Les tables existent : Testez l'accès à `/admin/`
- [ ] ✅ Le superutilisateur fonctionne : Connexion admin
- [ ] ✅ L'application fonctionne : Testez `/assets/tabulator/`
- [ ] ✅ Les fichiers statiques sont servis
- [ ] ✅ Pas d'erreurs dans les logs

## 🔄 Prévention Future

### 1. Script de Déploiement

Modifiez votre `deploy.sh` pour inclure :
```bash
# Toujours appliquer les migrations
python manage.py migrate --noinput

# Vérifier la configuration
python manage.py check --deploy
```

### 2. Variables d'Environnement

Créez un fichier `.env` avec :
```bash
DJANGO_SETTINGS_MODULE=site_trading_v3.settings.production
DEBUG=False
ALLOWED_HOSTS=votre_domaine.com,www.votre_domaine.com
```

### 3. Monitoring

Ajoutez des logs dans vos vues :
```python
import logging
logger = logging.getLogger(__name__)

def asset_tabulator(request):
    logger.info("Accès à asset_tabulator")
    # ... votre code
```

## 📞 Support

Si vous avez encore des problèmes :

1. **Vérifiez les logs** : `tail -f logs/django.log`
2. **Testez en mode debug** : Temporairement `DEBUG=True`
3. **Contactez votre hébergeur** : Ils peuvent avoir des spécificités
4. **Partagez les erreurs complètes** : Avec les tracebacks complets

## 📁 Fichiers Créés

Ce guide a créé les fichiers suivants :
- `setup_database_production.py` : Script Python complet
- `quick_fix_production.sh` : Script bash rapide
- `GUIDE_RESOLUTION_ERREUR_DB.md` : Ce guide

Gardez ces fichiers pour les futurs déploiements !
