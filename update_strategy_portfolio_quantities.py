#!/usr/bin/env python
"""
Script pour mettre à jour les quantités de portefeuille de toutes les stratégies existantes
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings.development')
django.setup()

from trading_app.models import Strategy

def update_all_strategy_portfolio_quantities():
    """Met à jour les quantités de portefeuille pour toutes les stratégies"""
    print("🔄 Mise à jour des quantités de portefeuille pour toutes les stratégies...")
    
    strategies = Strategy.objects.all()
    total_strategies = strategies.count()
    updated_count = 0
    
    print(f"📊 {total_strategies} stratégies trouvées")
    
    for strategy in strategies:
        try:
            print(f"\n🔍 Stratégie: {strategy.name}")
            print(f"   Asset: {strategy.asset.symbol}")
            print(f"   Quantité actuelle: {strategy.portfolio_quantity}")
            
            # Calculer la nouvelle quantité
            new_quantity = strategy.calculate_portfolio_quantity()
            
            print(f"   Nouvelle quantité: {new_quantity}")
            
            if new_quantity != -1:
                updated_count += 1
                print(f"   ✅ Mise à jour réussie")
            else:
                print(f"   ⚠️ Erreur ou pas de correspondance")
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
    
    print(f"\n🎯 Mise à jour terminée ! {updated_count}/{total_strategies} stratégies mises à jour.")
    return updated_count, total_strategies

def show_final_portfolio_quantities():
    """Affiche les quantités finales de portefeuille des stratégies"""
    print("\n📊 Quantités finales de portefeuille des stratégies :")
    print("-" * 80)
    print(f"{'Stratégie':<20} | {'Asset':<15} | {'Quantité':<15} | {'Utilisateur':<15}")
    print("-" * 80)
    
    for strategy in Strategy.objects.all().select_related('asset', 'user'):
        print(f"{strategy.name:<20} | {strategy.asset.symbol:<15} | {strategy.portfolio_quantity:<15} | {strategy.user.username:<15}")

if __name__ == "__main__":
    print("🚀 Script de mise à jour des quantités de portefeuille des stratégies")
    print("=" * 80)
    
    # Mettre à jour toutes les stratégies
    updated_count, total_strategies = update_all_strategy_portfolio_quantities()
    
    # Afficher l'état final
    show_final_portfolio_quantities()
    
    print(f"\n✅ Script terminé avec succès !")
    print(f"📈 Résumé: {updated_count}/{total_strategies} stratégies mises à jour")

