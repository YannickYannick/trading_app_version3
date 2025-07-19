#!/usr/bin/env python
"""
Script pour exécuter Django en mode production.
Usage: python run_production.py [command]
"""
import os
import sys

def main():
    """Run Django in production mode."""
    # Définir les paramètres de production
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "site_trading_v3.settings.production")
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main() 