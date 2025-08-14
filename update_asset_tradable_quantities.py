#!/usr/bin/env python
"""
Script pour mettre à jour les quantités des AssetTradable existants
basé sur les positions ouvertes actuelles
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings.development')
django.setup()

from trading_app.models import AssetTradable, Position

def update_all_asset_tradable_quantities():
    """Met à jour les quantités de tous les AssetTradable"""
    print("🔄 Mise à jour des quantités des AssetTradable...")
    
    updated_count = 0
    total_asset_tradables = AssetTradable.objects.count()
    
    for asset_tradable in AssetTradable.objects.all():
        try:
            # Calculer la quantité totale des positions ouvertes
            total_quantity = Position.objects.filter(
                asset_tradable=asset_tradable,
                status='OPEN'
            ).aggregate(
                total=django.db.models.Sum('size')
            )['total'] or 0
            
            # Mettre à jour le champ quantity
            asset_tradable.quantity = total_quantity
            asset_tradable.save(update_fields=['quantity'])
            
            print(f"   ✅ {asset_tradable.symbol} ({asset_tradable.platform}): {total_quantity}")
            updated_count += 1
            
        except Exception as e:
            print(f"   ❌ Erreur pour {asset_tradable.symbol}: {e}")
    
    print(f"\n🎯 Mise à jour terminée ! {updated_count}/{total_asset_tradables} AssetTradable mis à jour.")

def show_current_quantities():
    """Affiche les quantités actuelles des AssetTradable"""
    print("\n📊 Quantités actuelles des AssetTradable :")
    print("-" * 60)
    
    for asset_tradable in AssetTradable.objects.all().order_by('platform', 'symbol'):
        print(f"{asset_tradable.platform:8} | {asset_tradable.symbol:15} | {asset_tradable.quantity:>10}")

if __name__ == "__main__":
    print("🚀 Script de mise à jour des quantités AssetTradable")
    print("=" * 60)
    
    # Afficher l'état actuel
    show_current_quantities()
    
    # Mettre à jour les quantités
    update_all_asset_tradable_quantities()
    
    # Afficher l'état final
    show_current_quantities()
    
    print("\n✅ Script terminé avec succès !")

