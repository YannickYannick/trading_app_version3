import os
import sys

# Ajoute le répertoire du projet au chemin d'accès
sys.path.insert(0, os.path.dirname(__file__))

# Ajoute le chemin vers le répertoire du projet Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'site_trading_v3'))

# Définir le paramètre d'environnement pour les paramètres de Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'site_trading_v3.settings.production'

# Importer l'application WSGI depuis le fichier wsgi.py du projet
from site_trading_v3.wsgi import application 