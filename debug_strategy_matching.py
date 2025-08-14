#!/usr/bin/env python
"""
Script de debug pour comprendre le matching entre stratégies et AssetTradable
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings.development')
django.setup()

from trading_app.models import Strategy, AssetTradable

def debug_strategy_matching():
    """Debug le matching entre stratégies et AssetTradable"""
    print("🔍 Debug du matching entre stratégies et AssetTradable")
    print("=" * 80)
    
    # Vérifier tous les AssetTradable
    print("\n📊 AssetTradable disponibles :")
    print("-" * 60)
    for at in AssetTradable.objects.all():
        print(f"   {at.symbol} ({at.platform}) - Quantité: {at.quantity}")
    
    # Vérifier toutes les stratégies
    print("\n📊 Stratégies disponibles :")
    print("-" * 60)
    for strategy in Strategy.objects.all():
        print(f"   {strategy.name} - Asset: {strategy.asset.symbol}")
        
        # Tester le matching
        asset_symbol = strategy.asset.symbol
        base_symbol = asset_symbol.split(':')[0].split('_')[0].upper()
        
        print(f"      Symbole de base: {base_symbol}")
        
        # Chercher les AssetTradable correspondants
        matching_assets = AssetTradable.objects.filter(
            symbol__startswith=base_symbol
        )
        
        print(f"      AssetTradable trouvés: {matching_assets.count()}")
        for ma in matching_assets:
            print(f"         - {ma.symbol} ({ma.platform}) - Quantité: {ma.quantity}")
        
        # Calculer la quantité totale
        total_quantity = sum(float(ma.quantity or 0) for ma in matching_assets)
        print(f"      Quantité totale: {total_quantity}")

if __name__ == "__main__":
    debug_strategy_matching()

