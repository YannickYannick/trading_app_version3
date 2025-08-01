#!/usr/bin/env python
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings.development')
django.setup()

from trading_app.models import AllAssets
from django.db.models import Q

def test_search():
    print("🔍 Test de recherche dans AllAssets")
    
    # Test 1: Recherche par symbole
    print("\n1. Recherche 'AAPL':")
    results = AllAssets.objects.filter(
        Q(symbol__icontains='AAPL') | Q(name__icontains='AAPL')
    )[:5]
    for r in results:
        print(f"  - {r.symbol} - {r.name} ({r.platform})")
    
    # Test 2: Recherche 'BTC'
    print("\n2. Recherche 'BTC':")
    results = AllAssets.objects.filter(
        Q(symbol__icontains='BTC') | Q(name__icontains='BTC')
    )[:5]
    for r in results:
        print(f"  - {r.symbol} - {r.name} ({r.platform})")
    
    # Test 3: Recherche 'ETH'
    print("\n3. Recherche 'ETH':")
    results = AllAssets.objects.filter(
        Q(symbol__icontains='ETH') | Q(name__icontains='ETH')
    )[:5]
    for r in results:
        print(f"  - {r.symbol} - {r.name} ({r.platform})")
    
    # Test 4: Statistiques générales
    print(f"\n4. Statistiques:")
    print(f"  - Total actifs: {AllAssets.objects.count()}")
    print(f"  - Actifs Binance: {AllAssets.objects.filter(platform='binance').count()}")
    print(f"  - Actifs Saxo: {AllAssets.objects.filter(platform='saxo').count()}")
    print(f"  - Actifs tradables: {AllAssets.objects.filter(is_tradable=True).count()}")

if __name__ == "__main__":
    test_search() 