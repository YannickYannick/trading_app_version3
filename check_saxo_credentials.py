#!/usr/bin/env python3
"""
Script pour vérifier les credentials Saxo stockés dans la base de données
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings')
django.setup()

from trading_app.models import BrokerCredentials, User

def check_saxo_credentials():
    """Vérifier les credentials Saxo dans la base de données"""
    
    print("🔍 VÉRIFICATION DES CREDENTIALS SAXO DANS LA BASE DE DONNÉES")
    print("=" * 70)
    
    # 1. Vérifier les utilisateurs
    users = User.objects.all()
    print(f"👥 Utilisateurs trouvés: {len(users)}")
    for user in users:
        print(f"   - {user.username} (ID: {user.id})")
    
    # 2. Vérifier les credentials Saxo
    saxo_creds = BrokerCredentials.objects.filter(broker_type='saxo')
    print(f"\n🏦 Credentials Saxo trouvés: {len(saxo_creds)}")
    
    if not saxo_creds.exists():
        print("❌ Aucun credential Saxo trouvé !")
        return
    
    for cred in saxo_creds:
        print(f"\n📋 Broker: {cred.name} (ID: {cred.id})")
        print(f"   Utilisateur: {cred.user.username}")
        print(f"   Environnement: {getattr(cred, 'saxo_environment', 'Non défini')}")
        print(f"   Client ID: {cred.saxo_client_id}")
        print(f"   Client Secret: {'✅ Présent' if cred.saxo_client_secret else '❌ Absent'}")
        print(f"   Access Token: {'✅ Présent' if cred.saxo_access_token else '❌ Absent'}")
        print(f"   Refresh Token: {'✅ Présent' if cred.saxo_refresh_token else '❌ Absent'}")
        print(f"   Expire le: {cred.saxo_token_expires_at}")
        
        if cred.saxo_access_token and cred.saxo_refresh_token:
            print(f"   Tokens identiques: {'⚠️ OUI (Token 24h)' if cred.saxo_access_token == cred.saxo_refresh_token else '✅ NON (Refresh possible)'}")
        
        # Afficher les premiers caractères des tokens pour vérification
        if cred.saxo_access_token:
            print(f"   Access Token (20 premiers): {cred.saxo_access_token[:20]}...")
        if cred.saxo_refresh_token:
            print(f"   Refresh Token (20 premiers): {cred.saxo_refresh_token[:20]}...")
        if cred.saxo_client_secret:
            print(f"   Client Secret (10 premiers): {cred.saxo_client_secret[:10]}...")
    
    print("\n" + "=" * 70)
    print("💡 Prochaines étapes:")
    print("   1. Vérifiez que les Client ID et Client Secret sont corrects")
    print("   2. Vérifiez que le Refresh Token n'est pas expiré")
    print("   3. Testez avec les vrais credentials depuis Saxo")

if __name__ == "__main__":
    check_saxo_credentials()
