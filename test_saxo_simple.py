#!/usr/bin/env python3
"""
Test simple du refresh token Saxo Bank
"""

import requests
import json
from datetime import datetime

def test_saxo_refresh():
    """Test simple du refresh token Saxo"""
    
    print("🔍 TEST SIMPLE REFRESH TOKEN SAXO BANK")
    print("=" * 50)
    
    # Configuration de test (à adapter selon vos credentials)
    test_config = {
        'simulation': {
            'auth_url': 'https://sim.logonvalidation.net',
            'client_id': 'da4fe51ad5d641c6bb0048002049783b',
            'client_secret': 'tkt',
            'refresh_token': 'dbccb4e1-7038-4dec-b832-90f9014789ba'
        },
        'live': {
            'auth_url': 'https://live.logonvalidation.net',
            'client_id': 'da4fe51ad5d641c6bb0048002049783b',
            'client_secret': 'eyJhbGciOiJFUzI1NiIsIng1dCI6IjczMEZDMUQwMUQ0MzM5Q0JGRTU3MTc0Q0NGREQ0RjExRDZENzgwNDYifQ.eyJvYWEiOiI3Nzc3MCIsImlzcyI6Im9hIiwiYWlkIjoiMTY3NSIsInVpZCI6InJ2V2JqNXEwMlo4T21vfHVVOWNKVHc9PSIsImNpZCI6InJ2V2JqNXEwMlo4T21vfHVVOWNKVHc9PSIsImlzYSI6IkZhbHNlIiwidGlkIjoiMzY1NiIsInNpZCI6ImU3YmU3OGI2MDY2YTQ3NTk4OTM3MzYzN2YxMWM2ZDJhIiwiZGdpIjoiODQiLCJleHAiOiIxNzU1NzI2MzMyIiwib2FsIjoiMkYiLCJpaWQiOiIyMzI5ZjQzODVlMGI0ZGM2MWNjNjA4ZGQ2OTMyODM5OCJ9.apM6qb2OecKxshfv9_gzxUShJF1Sjvp0oQ5efnenbVtDlx7j_sx6hEkdEvOZbmviP9dVFeVSJmMHlC2GOSlw2A',
            'refresh_token': 'dbccb4e1-7038-4dec-b832-90f9014789ba'
        }
    }
    
    # Test de connectivité de base
    print("🔌 Test de connectivité de base...")
    
    for env, config in test_config.items():
        print(f"\n📡 Test {env.upper()}:")
        print(f"   URL: {config['auth_url']}")
        
        # Test GET simple
        try:
            response = requests.get(f"{config['auth_url']}/authorize", timeout=10)
            print(f"   ✅ GET /authorize: {response.status_code}")
        except Exception as e:
            print(f"   ❌ GET /authorize: {e}")
        
        # Test POST vers /token (sans credentials)
        try:
            response = requests.post(f"{config['auth_url']}/token", timeout=10)
            print(f"   📊 POST /token (sans auth): {response.status_code}")
            if response.status_code != 200:
                print(f"   📄 Réponse: {response.text[:200]}...")
        except Exception as e:
            print(f"   ❌ POST /token: {e}")
    
    print("\n" + "=" * 50)
    print("💡 Pour tester avec vos vrais credentials:")
    print("   1. Remplacez VOTRE_CLIENT_ID_* par vos vrais client IDs")
    print("   2. Remplacez VOTRE_CLIENT_SECRET_* par vos vrais client secrets")
    print("   3. Remplacez VOTRE_REFRESH_TOKEN_* par vos vrais refresh tokens")
    print("   4. Relancez le script")

if __name__ == "__main__":
    test_saxo_refresh()
