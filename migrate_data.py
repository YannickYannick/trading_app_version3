import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings.development')
django.setup()

from trading_app.models import Asset, AssetTradable, AssetType, Market

def migrate_old_data():
    """Migre les anciennes données vers la nouvelle structure"""
    
    # Créer les types et marchés par défaut
    default_type, _ = AssetType.objects.get_or_create(name='Unknown')
    default_market, _ = Market.objects.get_or_create(name='Unknown')
    
    # Récupérer tous les anciens Asset
    old_assets = Asset.objects.all()
    
    for old_asset in old_assets:
        print(f"Migration de {old_asset.symbol}...")
        
        # Créer l'AssetTradable correspondant
        AssetTradable.objects.get_or_create(
            symbol=old_asset.symbol,
            platform='saxo',  # Par défaut
            defaults={
                'asset': old_asset,
                'name': old_asset.name,
                'asset_type': default_type,
                'market': default_market,
            }
        )
    
    print("Migration terminée !")

if __name__ == "__main__":
    migrate_old_data() 