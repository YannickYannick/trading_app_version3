#!/usr/bin/env python
"""
Script pour calculer les quantités des AssetTradable en utilisant la logique complète
qui prend en compte positions et ordres en attente
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings.development')
django.setup()

from trading_app.models import AssetTradable, Position, PendingOrder, User
from django.db.models import Sum

def calculate_asset_tradable_quantities():
    """Calcule les quantités des AssetTradable en utilisant la logique complète"""
    print("🔄 Calcul des quantités des AssetTradable avec logique complète...")
    
    # Récupérer tous les utilisateurs
    users = User.objects.all()
    
    for user in users:
        print(f"\n👤 Utilisateur: {user.username}")
        print("-" * 60)
        
        try:
            # Récupérer tous les AssetTradable de l'utilisateur
            asset_tradables = AssetTradable.objects.filter(
                # Filtrer par les positions de l'utilisateur
                position__user=user
            ).distinct()
            
            # Ajouter les AssetTradable des pending orders
            pending_order_assets = AssetTradable.objects.filter(
                pendingorder__user=user
            ).distinct()
            
            # Combiner les deux querysets
            asset_tradables = list(asset_tradables) + list(pending_order_assets)
            # Supprimer les doublons basés sur l'ID
            seen_ids = set()
            unique_asset_tradables = []
            for asset in asset_tradables:
                if asset.id not in seen_ids:
                    seen_ids.add(asset.id)
                    unique_asset_tradables.append(asset)
            asset_tradables = unique_asset_tradables
            
            if not asset_tradables:
                print("   ⚠️ Aucun AssetTradable trouvé pour cet utilisateur")
                continue
            
            print(f"   📊 {len(asset_tradables)} AssetTradable uniques trouvés")
            
            for asset_tradable in asset_tradables:
                print(f"\n   🔍 Traitement de {asset_tradable.symbol} ({asset_tradable.platform})")
                
                # Récupérer les positions pour cet asset
                positions = Position.objects.filter(
                    user=user,
                    asset_tradable=asset_tradable
                )
                
                # Récupérer les pending orders pour cet asset
                pending_orders = PendingOrder.objects.filter(
                    user=user,
                    asset_tradable=asset_tradable
                ).select_related('broker_credentials')
                
                # Calculer les totaux
                total_position_size = sum(float(pos.size) for pos in positions)
                total_pending_quantity = sum(float(order.original_quantity) for order in pending_orders)
                
                # Calculer le net (positions + pending orders)
                # Les positions BUY et pending orders BUY sont positives
                # Les positions SELL et pending orders SELL sont négatives
                net_position = 0.0
                
                print(f"      📈 Positions ({positions.count()}):")
                for pos in positions:
                    if pos.side == 'BUY':
                        net_position += float(pos.size)
                        print(f"         + {pos.size} BUY @ {pos.entry_price}")
                    else:  # SELL
                        net_position -= float(pos.size)
                        print(f"         - {pos.size} SELL @ {pos.entry_price}")
                
                print(f"      📋 Ordres en attente ({pending_orders.count()}):")
                for order in pending_orders:
                    if order.side == 'BUY':
                        net_position += float(order.original_quantity)
                        print(f"         + {order.original_quantity} BUY ({order.order_type})")
                    else:  # SELL
                        net_position -= float(order.original_quantity)
                        print(f"         - {order.original_quantity} SELL ({order.order_type})")
                
                print(f"      🎯 Net total: {net_position:.6f}")
                
                # Mettre à jour le champ quantity de l'AssetTradable
                old_quantity = asset_tradable.quantity
                asset_tradable.quantity = net_position
                asset_tradable.save(update_fields=['quantity'])
                
                print(f"      ✅ AssetTradable mis à jour: {old_quantity} → {net_position:.6f}")
                
        except Exception as e:
            print(f"   ❌ Erreur pour l'utilisateur {user.username}: {e}")
    
    print(f"\n🎯 Calcul terminé pour tous les utilisateurs !")

def show_final_quantities():
    """Affiche les quantités finales des AssetTradable"""
    print("\n📊 Quantités finales des AssetTradable :")
    print("-" * 80)
    print(f"{'Platform':<10} | {'Symbol':<20} | {'Quantity':<15} | {'Positions':<10} | {'Pending Orders':<15}")
    print("-" * 80)
    
    for asset_tradable in AssetTradable.objects.all().order_by('platform', 'symbol'):
        # Compter les positions et ordres en attente
        total_positions = Position.objects.filter(asset_tradable=asset_tradable).count()
        total_pending = PendingOrder.objects.filter(asset_tradable=asset_tradable).count()
        
        print(f"{asset_tradable.platform:<10} | {asset_tradable.symbol:<20} | {asset_tradable.quantity:<15} | {total_positions:<10} | {total_pending:<15}")

def verify_specific_assets():
    """Vérifie spécifiquement AAPL et GOOGL"""
    print("\n🍎 Vérification spécifique AAPL/GOOGL :")
    print("-" * 60)
    
    # Chercher les AssetTradable pour AAPL et GOOGL
    aapl_asset = AssetTradable.objects.filter(symbol__startswith='AAPL').first()
    googl_asset = AssetTradable.objects.filter(symbol__startswith='GOOGL').first()
    
    if aapl_asset:
        print(f"   AAPL:XNAS - Quantité AssetTradable: {aapl_asset.quantity}")
        aapl_positions = Position.objects.filter(asset_tradable=aapl_asset)
        aapl_pending = PendingOrder.objects.filter(asset_tradable=aapl_asset)
        print(f"      Positions: {aapl_positions.count()}, Pending Orders: {aapl_pending.count()}")
        
        for pos in aapl_positions:
            print(f"         - {pos.size} {pos.side} @ {pos.entry_price} (User: {pos.user.username})")
        for order in aapl_pending:
            print(f"         - {order.original_quantity} {order.side} ({order.order_type}) (User: {order.user.username})")
    
    if googl_asset:
        print(f"   GOOGL:XNAS - Quantité AssetTradable: {googl_asset.quantity}")
        googl_positions = Position.objects.filter(asset_tradable=googl_asset)
        googl_pending = PendingOrder.objects.filter(asset_tradable=googl_asset)
        print(f"      Positions: {googl_positions.count()}, Pending Orders: {googl_pending.count()}")
        
        for pos in googl_positions:
            print(f"         - {pos.size} {pos.side} @ {pos.entry_price} (User: {pos.user.username})")
        for order in googl_pending:
            print(f"         - {order.original_quantity} {order.side} ({order.order_type}) (User: {order.user.username})")

if __name__ == "__main__":
    print("🚀 Script de calcul complet des quantités AssetTradable")
    print("=" * 80)
    
    # Vérifier l'état actuel
    verify_specific_assets()
    
    # Calculer les quantités
    calculate_asset_tradable_quantities()
    
    # Afficher l'état final
    show_final_quantities()
    verify_specific_assets()
    
    print("\n✅ Script terminé avec succès !")

