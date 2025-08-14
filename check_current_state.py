#!/usr/bin/env python
"""
Script pour vérifier l'état actuel des AssetTradable Saxo
Ce script affiche un rapport détaillé avant le nettoyage
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings')
django.setup()

from trading_app.models import AssetTradable, Position, AllAssets
from collections import defaultdict

def check_current_state():
    """Vérifie l'état actuel des AssetTradable Saxo"""
    print("🔍 Vérification de l'état actuel des AssetTradable Saxo...")
    
    # Récupérer tous les AssetTradable Saxo
    saxo_asset_tradables = AssetTradable.objects.filter(platform='saxo').order_by('symbol')
    print(f"📊 {saxo_asset_tradables.count()} AssetTradable Saxo trouvés")
    
    if saxo_asset_tradables.count() == 0:
        print("✅ Aucun AssetTradable Saxo trouvé")
        return
    
    # Grouper par AllAssets
    grouped_by_all_asset = defaultdict(list)
    for at in saxo_asset_tradables:
        if at.all_asset:
            grouped_by_all_asset[at.all_asset.id].append(at)
        else:
            print(f"⚠️ AssetTradable {at.symbol} sans AllAssets associé")
    
    print(f"\n📋 Répartition par AllAssets:")
    
    total_duplicates = 0
    total_positions = 0
    
    for all_asset_id, asset_tradables in grouped_by_all_asset.items():
        all_asset = asset_tradables[0].all_asset
        count = len(asset_tradables)
        
        if count > 1:
            total_duplicates += 1
            print(f"🔄 AllAssets {all_asset_id} ({all_asset.symbol}): {count} AssetTradable")
            
            # Afficher les détails des duplicatas
            for i, at in enumerate(asset_tradables):
                positions_count = Position.objects.filter(asset_tradable=at).count()
                total_positions += positions_count
                print(f"   {i+1}. {at.symbol} (ID: {at.id}) - {positions_count} positions")
        else:
            positions_count = Position.objects.filter(asset_tradable=asset_tradables[0]).count()
            total_positions += positions_count
            print(f"✅ AllAssets {all_asset_id} ({all_asset.symbol}): 1 AssetTradable - {positions_count} positions")
    
    print(f"\n📊 Résumé:")
    print(f"   📈 Total AssetTradable Saxo: {saxo_asset_tradables.count()}")
    print(f"   🔄 Groupes avec doublons: {total_duplicates}")
    print(f"   📋 Total positions Saxo: {total_positions}")
    
    # Calculer l'économie potentielle
    if total_duplicates > 0:
        total_duplicate_assets = sum(len(ats) - 1 for ats in grouped_by_all_asset.values() if len(ats) > 1)
        print(f"   🗑️ AssetTradable à supprimer: {total_duplicate_assets}")
        print(f"   💾 Économie de stockage: ~{total_duplicate_assets * 100} bytes")

def show_sample_duplicates():
    """Affiche quelques exemples de doublons"""
    print("\n🔍 Exemples de doublons trouvés:")
    
    saxo_asset_tradables = AssetTradable.objects.filter(platform='saxo')
    grouped_by_all_asset = defaultdict(list)
    
    for at in saxo_asset_tradables:
        if at.all_asset:
            grouped_by_all_asset[at.all_asset.id].append(at)
    
    count = 0
    for all_asset_id, asset_tradables in grouped_by_all_asset.items():
        if len(asset_tradables) > 1 and count < 5:  # Limiter à 5 exemples
            all_asset = asset_tradables[0].all_asset
            print(f"\n📌 {all_asset.symbol} ({all_asset.name}):")
            
            for at in asset_tradables:
                positions_count = Position.objects.filter(asset_tradable=at).count()
                print(f"   - {at.symbol} (ID: {at.id}) - {positions_count} positions")
            
            count += 1

if __name__ == "__main__":
    print("🚀 Vérification de l'état actuel...")
    
    try:
        check_current_state()
        show_sample_duplicates()
        print("\n✅ Vérification terminée!")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de la vérification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


