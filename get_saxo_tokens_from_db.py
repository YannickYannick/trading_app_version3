#!/usr/bin/env python3
"""
Script pour récupérer les tokens Saxo depuis la base de données et tester le refresh
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings')
django.setup()

from trading_app.models import BrokerCredentials, User

def get_saxo_tokens_from_db():
    """Récupérer les tokens Saxo depuis la base de données"""
    
    print("🔍 RÉCUPÉRATION DES TOKENS SAXO DEPUIS LA BASE DE DONNÉES")
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
        return None
    
    for cred in saxo_creds:
        print(f"\n📋 Broker: {cred.name} (ID: {cred.id})")
        print(f"   Utilisateur: {cred.user.username}")
        print(f"   Environnement: {getattr(cred, 'saxo_environment', 'Non défini')}")
        print(f"   Client ID: {cred.saxo_client_id}")
        print(f"   Access Token: {'✅ Présent' if cred.saxo_access_token else '❌ Absent'}")
        print(f"   Refresh Token: {'✅ Présent' if cred.saxo_refresh_token else '❌ Absent'}")
        print(f"   Expire le: {cred.saxo_token_expires_at}")
        
        if cred.saxo_access_token and cred.saxo_refresh_token:
            print(f"   Tokens identiques: {'⚠️ OUI (Token 24h)' if cred.saxo_access_token == cred.saxo_refresh_token else '✅ NON (Refresh possible)'}")
            
            # Si c'est un vrai refresh token, l'utiliser pour le test
            if cred.saxo_access_token != cred.saxo_refresh_token:
                print(f"   🔄 Refresh Token disponible pour test: {cred.saxo_refresh_token[:20]}...")
                return {
                    'client_id': cred.saxo_client_id,
                    'client_secret': cred.saxo_client_secret,
                    'refresh_token': cred.saxo_refresh_token,
                    'environment': getattr(cred, 'saxo_environment', 'simulation'),
                    'broker_name': cred.name
                }
    
    print("\n❌ Aucun refresh token valide trouvé pour les tests")
    return None

def test_refresh_with_real_token(token_info):
    """Tester le refresh avec un vrai token depuis la DB"""
    
    print(f"\n🧪 TEST DE REFRESH AVEC LE VRAI TOKEN DE {token_info['broker_name']}")
    print("=" * 70)
    
    import requests
    
    # Configuration selon l'environnement
    if token_info['environment'] == 'live':
        token_url = "https://live.logonvalidation.net/token"
        environment_name = "LIVE"
    else:
        token_url = "https://sim.logonvalidation.net/token"
        environment_name = "SIMULATION"
    
    print(f"🔑 Environment: {environment_name}")
    print(f"🔑 Client ID: {token_info['client_id']}")
    print(f"🔑 Token URL: {token_url}")
    print(f"🔑 Refresh Token: {token_info['refresh_token'][:20]}...")
    
    # Test de refresh
    data = {
        "grant_type": "refresh_token",
        "refresh_token": token_info['refresh_token'],
        "client_id": token_info['client_id'],
        "client_secret": token_info['client_secret']
    }
    
    print(f"\n📤 Données envoyées: {data}")
    
    try:
        print(f"📡 Envoi de la requête POST...")
        response = requests.post(
            token_url, 
            data=data, 
            timeout=30,
            headers={
                'User-Agent': 'SaxoBroker/1.0',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Headers de réponse: {dict(response.headers)}")
        print(f"📄 Contenu de la réponse: {response.text}")
        
        if response.status_code in [200, 201]:
            try:
                tokens = response.json()
                print("✅ Refresh réussi !")
                print(f"🔑 Nouveau Access Token: {tokens.get('access_token', 'N/A')[:50]}...")
                print(f"🔑 Nouveau Refresh Token: {tokens.get('refresh_token', 'N/A')}")
                print(f"⏰ Expire dans: {tokens.get('expires_in', 'N/A')} secondes")
                print(f"🔄 Refresh Token expire dans: {tokens.get('refresh_token_expires_in', 'N/A')} secondes")
                
                # Test de l'access token avec l'API Saxo
                print(f"\n🧪 Test de l'access token avec l'API Saxo...")
                access_token = tokens.get('access_token')
                if access_token:
                    test_api_with_token(access_token, environment_name)
                else:
                    print("❌ Pas d'access token reçu")
                    
                return tokens
                    
            except Exception as e:
                print(f"❌ Erreur parsing JSON: {e}")
                print(f"📄 Contenu brut: {response.text}")
                return None
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            print(f"📄 Réponse: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Erreur lors du refresh: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_api_with_token(access_token, environment):
    """Tester l'access token avec l'API Saxo"""
    
    if environment == 'LIVE':
        api_url = "https://gateway.saxobank.com/openapi/port/v1/accounts/me"
    else:
        api_url = "https://gateway.saxobank.com/sim/openapi/port/v1/accounts/me"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        print(f"🌐 Test API: {api_url}")
        response = requests.get(api_url, headers=headers, timeout=30)
        
        print(f"📊 Status Code API: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API accessible avec le nouveau token !")
            print(f"📊 Données reçues: {data}")
        else:
            print(f"❌ Erreur API: {response.status_code}")
            print(f"📄 Réponse API: {response.text}")
            
    except Exception as e:
        print(f"❌ Erreur test API: {e}")

if __name__ == "__main__":
    print("🚀 Démarrage de la récupération des tokens Saxo...")
    
    # Récupérer les tokens depuis la DB
    token_info = get_saxo_tokens_from_db()
    
    if token_info:
        # Tester le refresh
        new_tokens = test_refresh_with_real_token(token_info)
        
        if new_tokens:
            print(f"\n🎉 SUCCÈS ! Le refresh token fonctionne parfaitement !")
            print(f"💡 Vous pouvez maintenant utiliser ces tokens dans votre application")
        else:
            print(f"\n❌ ÉCHEC du refresh token")
    else:
        print(f"\n❌ Impossible de récupérer les tokens depuis la base de données")
    
    print("\n" + "=" * 70)
    print("🏁 Script terminé")
