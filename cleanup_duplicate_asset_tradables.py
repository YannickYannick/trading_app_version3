#!/usr/bin/env python
"""
Script pour nettoyer les AssetTradable en double et consolider les positions Saxo
Ce script va :
1. Identifier les AssetTradable en double pour Saxo
2. Consolider les positions vers un seul AssetTradable par AllAssets
3. Supprimer les AssetTradable en double
"""

import os
import sys
import django
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings')
django.setup()

from trading_app.models import AssetTradable, Position, AllAssets
from django.db import transaction
from collections import defaultdict

def cleanup_duplicate_asset_tradables():
    """Nettoie les AssetTradable en double pour Saxo"""
    print("🧹 Nettoyage des AssetTradable en double pour Saxo...")
    
    # Récupérer tous les AssetTradable Saxo
    saxo_asset_tradables = AssetTradable.objects.filter(platform='saxo')
    print(f"📊 {saxo_asset_tradables.count()} AssetTradable Saxo trouvés")
    
    # Grouper par AllAssets
    grouped_by_all_asset = defaultdict(list)
    for at in saxo_asset_tradables:
        if at.all_asset:
            grouped_by_all_asset[at.all_asset.id].append(at)
        else:
            print(f"⚠️ AssetTradable {at.symbol} sans AllAssets associé")
    
    print(f"📋 {len(grouped_by_all_asset)} groupes d'AllAssets trouvés")
    
    total_consolidated = 0
    total_deleted = 0
    
    with transaction.atomic():
        for all_asset_id, asset_tradables in grouped_by_all_asset.items():
            if len(asset_tradables) == 1:
                print(f"✅ AllAssets {all_asset_id}: 1 AssetTradable (pas de nettoyage nécessaire)")
                continue
            
            print(f"🔄 AllAssets {all_asset_id}: {len(asset_tradables)} AssetTradable à consolider")
            
            # Trier par symbole pour identifier le principal (sans suffixe numérique)
            asset_tradables.sort(key=lambda x: x.symbol)
            
            # Le premier (sans suffixe numérique) sera conservé
            primary_asset_tradable = asset_tradables[0]
            duplicates = asset_tradables[1:]
            
            print(f"   📌 AssetTradable principal conservé: {primary_asset_tradable.symbol}")
            print(f"   🗑️ AssetTradable à supprimer: {[at.symbol for at in duplicates]}")
            
            # Consolider les positions des duplicatas vers le principal
            for duplicate in duplicates:
                # Récupérer toutes les positions liées à ce duplicata
                positions = Position.objects.filter(asset_tradable=duplicate)
                print(f"      📊 {positions.count()} positions à migrer depuis {duplicate.symbol}")
                
                # Migrer les positions vers l'AssetTradable principal
                for position in positions:
                    position.asset_tradable = primary_asset_tradable
                    position.save()
                    print(f"         ✅ Position migrée: {position.id}")
                
                # Supprimer l'AssetTradable duplicata
                duplicate.delete()
                total_deleted += 1
                print(f"         🗑️ AssetTradable supprimé: {duplicate.symbol}")
            
            total_consolidated += 1
    
    print(f"\n🎉 Nettoyage terminé!")
    print(f"   📊 Groupes consolidés: {total_consolidated}")
    print(f"   🗑️ AssetTradable supprimés: {total_deleted}")
    
    # Vérification finale
    final_count = AssetTradable.objects.filter(platform='saxo').count()
    print(f"   📈 AssetTradable Saxo restants: {final_count}")

def verify_consolidation():
    """Vérifie que la consolidation s'est bien passée"""
    print("\n🔍 Vérification de la consolidation...")
    
    # Vérifier qu'il n'y a plus de doublons
    saxo_asset_tradables = AssetTradable.objects.filter(platform='saxo')
    
    # Grouper par AllAssets
    grouped_by_all_asset = defaultdict(list)
    for at in saxo_asset_tradables:
        if at.all_asset:
            grouped_by_all_asset[at.all_asset.id].append(at)
    
    duplicates_found = False
    for all_asset_id, asset_tradables in grouped_by_all_asset.items():
        if len(asset_tradables) > 1:
            print(f"❌ Doublon trouvé pour AllAssets {all_asset_id}: {len(asset_tradables)} AssetTradable")
            for at in asset_tradables:
                print(f"   - {at.symbol} (ID: {at.id})")
            duplicates_found = True
    
    if not duplicates_found:
        print("✅ Aucun doublon trouvé - consolidation réussie!")
    
    # Vérifier les positions
    total_positions = Position.objects.count()
    saxo_positions = Position.objects.filter(asset_tradable__platform='saxo').count()
    print(f"📊 Total positions: {total_positions}")
    print(f"📊 Positions Saxo: {saxo_positions}")

if __name__ == "__main__":
    print("🚀 Début du nettoyage des AssetTradable en double...")
    
    try:
        cleanup_duplicate_asset_tradables()
        verify_consolidation()
        print("\n✅ Script terminé avec succès!")
        
    except Exception as e:
        print(f"\n❌ Erreur lors du nettoyage: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


