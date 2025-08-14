#!/usr/bin/env python
"""
Script pour forcer la mise à jour des quantités des AssetTradable
en utilisant la même logique que le tabulator des stratégies
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings.development')
django.setup()

from trading_app.models import AssetTradable, Position, AllAssets
from django.db.models import Sum

def force_update_asset_tradable_quantities():
    """Force la mise à jour des quantités en recalculant depuis les positions"""
    print("🔄 Force mise à jour des quantités des AssetTradable...")
    
    updated_count = 0
    total_asset_tradables = AssetTradable.objects.count()
    
    for asset_tradable in AssetTradable.objects.all():
        try:
            print(f"🔍 Traitement de {asset_tradable.symbol} ({asset_tradable.platform})")
            
            # Calculer la quantité totale des positions ouvertes pour cet utilisateur
            # On prend toutes les positions ouvertes liées à cet AssetTradable
            positions = Position.objects.filter(
                asset_tradable=asset_tradable,
                status='OPEN'
            )
            
            if positions.exists():
                # Calculer la somme totale des tailles
                total_quantity = positions.aggregate(
                    total=Sum('size')
                )['total'] or 0
                
                print(f"   📈 {positions.count()} positions ouvertes trouvées")
                for pos in positions:
                    print(f"      - {pos.size} @ {pos.entry_price} ({pos.side}) - User: {pos.user.username}")
                
                # Mettre à jour le champ quantity
                old_quantity = asset_tradable.quantity
                asset_tradable.quantity = total_quantity
                asset_tradable.save(update_fields=['quantity'])
                
                print(f"   ✅ Quantité mise à jour: {old_quantity} → {total_quantity}")
                updated_count += 1
            else:
                print(f"   ⚠️ Aucune position ouverte trouvée")
                # Mettre à jour à 0 si pas de positions
                if asset_tradable.quantity != 0:
                    asset_tradable.quantity = 0
                    asset_tradable.save(update_fields=['quantity'])
                    updated_count += 1
                    print(f"   ✅ Quantité mise à jour: {asset_tradable.quantity} → 0")
                
        except Exception as e:
            print(f"   ❌ Erreur pour {asset_tradable.symbol}: {e}")
    
    print(f"\n🎯 Mise à jour terminée ! {updated_count}/{total_asset_tradables} AssetTradable mis à jour.")

def show_current_quantities():
    """Affiche les quantités actuelles des AssetTradable"""
    print("\n📊 Quantités actuelles des AssetTradable :")
    print("-" * 80)
    print(f"{'Platform':<10} | {'Symbol':<20} | {'Quantity':<15} | {'Positions':<10}")
    print("-" * 80)
    
    for asset_tradable in AssetTradable.objects.all().order_by('platform', 'symbol'):
        # Compter les positions ouvertes
        open_positions = Position.objects.filter(
            asset_tradable=asset_tradable,
            status='OPEN'
        ).count()
        
        print(f"{asset_tradable.platform:<10} | {asset_tradable.symbol:<20} | {asset_tradable.quantity:<15} | {open_positions:<10}")

def verify_positions_exist():
    """Vérifie que les positions existent bien"""
    print("\n🔍 Vérification des positions existantes :")
    print("-" * 60)
    
    # Chercher toutes les positions ouvertes
    open_positions = Position.objects.filter(status='OPEN')
    
    if open_positions.exists():
        print(f"📈 {open_positions.count()} positions ouvertes trouvées :")
        for pos in open_positions:
            print(f"   - {pos.size} {pos.asset_tradable.symbol} ({pos.side}) - User: {pos.user.username}")
    else:
        print("⚠️ Aucune position ouverte trouvée !")
    
    # Vérifier spécifiquement AAPL et GOOGL
    print("\n🍎 Vérification spécifique AAPL/GOOGL :")
    
    # Chercher les AssetTradable pour AAPL et GOOGL
    aapl_asset = AssetTradable.objects.filter(symbol__startswith='AAPL').first()
    googl_asset = AssetTradable.objects.filter(symbol__startswith='GOOGL').first()
    
    if aapl_asset:
        aapl_positions = Position.objects.filter(
            asset_tradable=aapl_asset,
            status='OPEN'
        )
        print(f"   AAPL: {aapl_positions.count()} positions ouvertes, quantité AssetTradable: {aapl_asset.quantity}")
        for pos in aapl_positions:
            print(f"      - {pos.size} @ {pos.entry_price} ({pos.side})")
    
    if googl_asset:
        googl_positions = Position.objects.filter(
            asset_tradable=googl_asset,
            status='OPEN'
        )
        print(f"   GOOGL: {googl_positions.count()} positions ouvertes, quantité AssetTradable: {googl_asset.quantity}")
        for pos in googl_positions:
            print(f"      - {pos.size} @ {pos.entry_price} ({pos.side})")

if __name__ == "__main__":
    print("🚀 Script de force mise à jour des quantités AssetTradable")
    print("=" * 80)
    
    # Vérifier l'état actuel
    verify_positions_exist()
    show_current_quantities()
    
    # Forcer la mise à jour
    force_update_asset_tradable_quantities()
    
    # Afficher l'état final
    show_current_quantities()
    
    print("\n✅ Script terminé avec succès !")

