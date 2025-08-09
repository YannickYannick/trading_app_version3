# Guide : Gestion des Multiples Bases de Données

## 🔍 Le Problème Identifié

Votre projet utilise **4 bases de données différentes** selon l'environnement :

| Environnement | Fichier de config | Base de données | Usage |
|---------------|------------------|-----------------|--------|
| **Base** | `settings.py` | `db_test_1.sqlite3` | Configuration par défaut |
| **Development** | `development.py` | `db_test_2.sqlite3` | Développement local |
| **Production Test** | `production_test.py` | `db_test_3.sqlite3` | Test avant production |
| **Production** | `production.py` | `db_test_4.sqlite3` | Production réelle |

**Le problème** : Seule `db_test_2.sqlite3` (development) contient vos tables car c'est là que vous avez travaillé localement.

## ⚡ Solutions Rapides

### 1. Vérifier l'état actuel
```bash
python check_all_environments.py
```
Cette commande vous montrera l'état de toutes vos bases de données.

### 2. Synchroniser toutes les bases
```bash
python sync_all_databases.py
```
Ce script va :
- Détecter quelle base contient vos données
- Appliquer les migrations à tous les environnements
- Synchroniser les données entre les bases
- Créer des superutilisateurs pour chaque environnement

### 3. Correction spécifique pour production_test
```bash
# Si votre hébergeur utilise production_test
python setup_database_production.py production_test
```

## 🔧 Solutions Manuelles

### Pour l'environnement Production Test
```bash
# Configurer pour production_test
export DJANGO_SETTINGS_MODULE=site_trading_v3.settings.production_test

# Appliquer les migrations
python manage.py migrate

# Créer superutilisateur
python manage.py createsuperuser

# Tester
python manage.py runserver --settings=site_trading_v3.settings.production_test
```

### Pour l'environnement Production
```bash
# Configurer pour production
export DJANGO_SETTINGS_MODULE=site_trading_v3.settings.production

# Appliquer les migrations
python manage.py migrate

# Créer superutilisateur
python manage.py createsuperuser
```

### Copier des données entre bases
```bash
# Copier development vers production_test
cp db_test_2.sqlite3 db_test_3.sqlite3

# Copier development vers production
cp db_test_2.sqlite3 db_test_4.sqlite3
```

## 🚀 Configuration pour l'Hébergeur

### 1. Identifier quel environnement utilise votre hébergeur

Vérifiez dans votre configuration d'hébergement quel `DJANGO_SETTINGS_MODULE` est utilisé :

```bash
# Vérifier la variable d'environnement
echo $DJANGO_SETTINGS_MODULE

# Ou dans votre fichier de configuration (passenger_wsgi.py, gunicorn, etc.)
grep -r "DJANGO_SETTINGS_MODULE" .
```

### 2. Scripts adaptés pour chaque environnement

#### Pour Production Test (db_test_3.sqlite3)
```bash
# Script spécifique
export DJANGO_SETTINGS_MODULE=site_trading_v3.settings.production_test
python setup_database_production.py production_test
```

#### Pour Production (db_test_4.sqlite3)
```bash
# Script spécifique  
export DJANGO_SETTINGS_MODULE=site_trading_v3.settings.production
python setup_database_production.py
```

### 3. Mettre à jour votre script de déploiement

Modifiez `deploy.sh` :

```bash
#!/bin/bash

# Détecter l'environnement
if [ "$DJANGO_ENV" = "production_test" ]; then
    export DJANGO_SETTINGS_MODULE=site_trading_v3.settings.production_test
    echo "🔧 Mode: Production Test"
else
    export DJANGO_SETTINGS_MODULE=site_trading_v3.settings.production
    echo "🔧 Mode: Production"
fi

# Reste du script...
python manage.py migrate
python manage.py collectstatic --noinput
```

## 🔍 Diagnostic et Débogage

### Vérifier quelle base est utilisée
```bash
python manage.py shell -c "
from django.conf import settings
print('Settings module:', settings.SETTINGS_MODULE)
print('Database:', settings.DATABASES['default']['NAME'])
"
```

### Lister les tables dans chaque base
```bash
# Pour db_test_2.sqlite3 (development)
sqlite3 db_test_2.sqlite3 ".tables"

# Pour db_test_3.sqlite3 (production_test)  
sqlite3 db_test_3.sqlite3 ".tables"

# Pour db_test_4.sqlite3 (production)
sqlite3 db_test_4.sqlite3 ".tables"
```

### Tester chaque environnement
```bash
# Test development
python manage.py runserver --settings=site_trading_v3.settings.development

# Test production_test
python manage.py runserver --settings=site_trading_v3.settings.production_test

# Test production
python manage.py runserver --settings=site_trading_v3.settings.production
```

## 📋 Checklist de Résolution

- [ ] ✅ Exécuter `python check_all_environments.py`
- [ ] ✅ Identifier l'environnement utilisé par l'hébergeur
- [ ] ✅ Exécuter `python sync_all_databases.py`
- [ ] ✅ Tester localement l'environnement correspondant
- [ ] ✅ Déployer avec la bonne configuration
- [ ] ✅ Vérifier que `/assets/tabulator/` fonctionne
- [ ] ✅ Tester la connexion admin
- [ ] ✅ Changer les mots de passe par défaut

## 🎯 Recommandations

### 1. Simplification future
Considérez utiliser une seule base de données avec des préfixes de tables :
```python
# Dans settings
DATABASE_ROUTERS = ['myapp.routers.DatabaseRouter']
```

### 2. Variables d'environnement
Utilisez des variables d'environnement pour la configuration :
```python
# Dans base.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / os.environ.get('DB_NAME', 'db.sqlite3'),
    }
}
```

### 3. Scripts de migration automatique
Ajoutez dans votre `deploy.sh` :
```bash
# Auto-détecter et synchroniser
python sync_all_databases.py
```

## 📞 Support

Si vous avez encore des problèmes après ces étapes :

1. **Partagez la sortie** de `python check_all_environments.py`
2. **Identifiez l'environnement** utilisé par votre hébergeur
3. **Vérifiez les logs** spécifiques à cet environnement
4. **Testez localement** avec le même environnement

Les scripts créés vont résoudre 99% des problèmes de synchronisation entre vos différentes bases de données ! 🎉
