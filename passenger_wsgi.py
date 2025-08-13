import os
import sys

# Ajoute le répertoire du projet au chemin d'accès
sys.path.insert(0, os.path.dirname(__file__))

# Ajoute le chemin vers le répertoire du projet Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'site_trading_v3'))

os.environ['DJANGO_SETTINGS_MODULE'] = 'site_trading_v3.settings.production_test'

from site_trading_v3.wsgi import application