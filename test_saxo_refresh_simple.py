#!/usr/bin/env python3
"""
Test simple du refresh token Saxo Bank basé sur l'exemple qui fonctionne
"""

import requests
import json
from datetime import datetime, timedelta

def test_saxo_refresh_simple():
    """Test simple du refresh token Saxo basé sur l'exemple qui marche"""
    
    print("🔍 TEST SIMPLE REFRESH TOKEN SAXO BANK")
    print("=" * 60)
    
    # Configuration de test (à adapter selon vos credentials)
    CLIENT_ID = "da4fe51ad5d641c6bb0048002049783b"  # Remplacez par votre vrai Client ID
    CLIENT_SECRET = "bc51e0f6cb54420a84d656a74e4536b3"  # Remplacez par votre vrai Client Secret
    REDIRECT_URI = "https://le-baff.com"
    TOKEN_URL = "https://live.logonvalidation.net/token"
    
    # Test avec un refresh token existant (à remplacer par un vrai)
    REFRESH_TOKEN = "a2c2184c-fa40-40a6-ae2c-a150e15d9738"  # Remplacez par un vrai refresh token
    
    print(f"🔑 Client ID: {CLIENT_ID}")
    print(f"🔑 Environment: LIVE")
    print(f"🔑 Token URL: {TOKEN_URL}")
    print(f"🔑 Refresh Token: {REFRESH_TOKEN[:20] if REFRESH_TOKEN != 'VOTRE_REFRESH_TOKEN_ICI' else 'NON FOURNI'}...")
    
    if REFRESH_TOKEN == "VOTRE_REFRESH_TOKEN_ICI":
        print("\n❌ Veuillez remplacer 'VOTRE_REFRESH_TOKEN_ICI' par un vrai refresh token")
        print("💡 Vous pouvez l'obtenir en vous connectant à Saxo et en regardant dans la base de données")
        return
    
    # Test de refresh
    print(f"\n🔄 Tentative de refresh du token...")
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    
    print(f"📤 Données envoyées: {data}")
    
    try:
        print(f"📡 Envoi de la requête POST...")
        response = requests.post(
            TOKEN_URL, 
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
                    test_api_with_token(access_token)
                else:
                    print("❌ Pas d'access token reçu")
                    
            except Exception as e:
                print(f"❌ Erreur parsing JSON: {e}")
                print(f"📄 Contenu brut: {response.text}")
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            print(f"📄 Réponse: {response.text}")
            
    except Exception as e:
        print(f"❌ Erreur lors du refresh: {e}")
        import traceback
        traceback.print_exc()

def test_api_with_token(access_token):
    """Tester l'access token avec l'API Saxo"""
    API_URL = "https://gateway.saxobank.com/openapi/port/v1/accounts/me"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        print(f"🌐 Test API: {API_URL}")
        response = requests.get(API_URL, headers=headers, timeout=30)
        
        print(f"📊 Status Code API: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API accessible avec le nouveau token !")
            print(f"📊 Données reçues: {json.dumps(data, indent=2)[:500]}...")
        else:
            print(f"❌ Erreur API: {response.status_code}")
            print(f"📄 Réponse API: {response.text}")
            
    except Exception as e:
        print(f"❌ Erreur test API: {e}")

def test_connectivity():
    """Test de connectivité de base"""
    print(f"\n🔌 Test de connectivité de base...")
    
    # Test endpoint d'auth
    try:
        response = requests.get("https://live.logonvalidation.net/authorize", timeout=10)
        print(f"✅ Endpoint d'auth accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Endpoint d'auth inaccessible: {e}")
    
    # Test endpoint token
    try:
        response = requests.post("https://live.logonvalidation.net/token", timeout=10)
        print(f"📊 Endpoint token accessible: {response.status_code} (sans auth)")
    except Exception as e:
        print(f"❌ Endpoint token inaccessible: {e}")

if __name__ == "__main__":
    print("🚀 Démarrage du test Saxo...")
    
    # Test de connectivité
    test_connectivity()
    
    # Test de refresh
    test_saxo_refresh_simple()
    
    print("\n" + "=" * 60)
    print("🏁 Test terminé")
    print("\n💡 Pour utiliser ce script:")
    print("   1. Remplacez CLIENT_ID et CLIENT_SECRET par vos vrais credentials")
    print("   2. Remplacez REFRESH_TOKEN par un vrai refresh token")
    print("   3. Relancez le script")
