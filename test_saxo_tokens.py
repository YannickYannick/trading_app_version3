#!/usr/bin/env python3
"""
Script de test pour vérifier la gestion des tokens Saxo (incluant tokens 24h)
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings.development')
django.setup()

from django.contrib.auth.models import User
from trading_app.models import BrokerCredentials
from trading_app.services import BrokerService

def test_saxo_tokens():
    """Test de la gestion des tokens Saxo"""
    print("=== TEST GESTION TOKENS SAXO ===")
    
    # Récupérer le premier utilisateur
    try:
        user = User.objects.first()
        if not user:
            print("❌ Aucun utilisateur trouvé")
            return
        
        print(f"👤 Utilisateur: {user.username}")
        
        # Récupérer les credentials Saxo
        broker_creds = BrokerCredentials.objects.filter(
            user=user, 
            broker_type='saxo',
            is_active=True
        ).first()
        
        if not broker_creds:
            print("❌ Aucune configuration Saxo trouvée")
            return
        
        print(f"🏦 Configuration Saxo: {broker_creds.name}")
        print(f"   Client ID: {broker_creds.saxo_client_id}")
        print(f"   Access Token: {'✅ Présent' if broker_creds.saxo_access_token else '❌ Absent'}")
        print(f"   Refresh Token: {'✅ Présent' if broker_creds.saxo_refresh_token else '❌ Absent'}")
        print(f"   Expire le: {broker_creds.saxo_token_expires_at}")
        
        # Test du service
        broker_service = BrokerService(user)
        broker = broker_service.get_broker_instance(broker_creds)
        
        print(f"\n🔧 Instance broker créée: {type(broker)}")
        print(f"   Access Token dans broker: {'✅ Présent' if broker.access_token else '❌ Absent'}")
        print(f"   Refresh Token dans broker: {'✅ Présent' if broker.refresh_token else '❌ Absent'}")
        
        # Test de détection token 24h
        if hasattr(broker, 'is_24h_token'):
            is_24h = broker.is_24h_token()
            print(f"   Token 24h détecté: {'✅ Oui' if is_24h else '❌ Non'}")
            
            if is_24h:
                print("🔑 Configuration token 24h détectée")
                print("   → Le système évitera les tentatives de refresh automatique")
        
        # Test d'authentification
        print(f"\n🔐 Test d'authentification...")
        is_auth = broker.authenticate()
        print(f"   Authentifié: {'✅ Oui' if is_auth else '❌ Non'}")
        
        if is_auth:
            print("✅ Les tokens sont valides !")
            
            # Test de récupération de données
            print(f"\n📊 Test de récupération de données...")
            try:
                accounts = broker.get_accounts()
                print(f"   Comptes récupérés: {len(accounts)}")
                
                positions = broker.get_positions()
                print(f"   Positions récupérées: {len(positions)}")
                
                print("✅ Récupération de données réussie !")
            except Exception as e:
                print(f"❌ Erreur lors de la récupération: {e}")
        else:
            print("❌ Les tokens ne sont pas valides ou manquants")
            print("💡 Vous pouvez :")
            print("   1. Saisir manuellement les tokens dans la configuration")
            print("   2. Utiliser le flux OAuth2 via l'interface web")
            print("   3. Pour un token 24h: mettre le même token dans access_token et refresh_token")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

def test_24h_token_simulation():
    """Simulation d'un token 24h"""
    print("\n=== SIMULATION TOKEN 24H ===")
    
    try:
        user = User.objects.first()
        if not user:
            print("❌ Aucun utilisateur trouvé")
            return
        
        # Créer une instance broker avec un token 24h simulé
        from trading_app.brokers.saxo import SaxoBroker
        
        # Token 24h simulé (format JWT typique)
        fake_24h_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        credentials = {
            'client_id': 'test_client',
            'client_secret': 'test_secret',
            'redirect_uri': 'http://localhost:8080/callback',
            'access_token': fake_24h_token,
            'refresh_token': fake_24h_token,  # Même token pour simuler un 24h
        }
        
        broker = SaxoBroker(user, credentials)
        
        print(f"🔧 Broker créé avec token 24h simulé")
        print(f"   Token 24h détecté: {'✅ Oui' if broker.is_24h_token() else '❌ Non'}")
        
        # Test d'authentification
        is_auth = broker.authenticate()
        print(f"   Authentification: {'✅ Réussie' if is_auth else '❌ Échouée'}")
        
        if is_auth:
            print("✅ Le token 24h est correctement géré !")
        else:
            print("❌ Problème avec la gestion du token 24h")
            
    except Exception as e:
        print(f"❌ Erreur simulation: {e}")

if __name__ == "__main__":
    test_saxo_tokens()
    test_24h_token_simulation() 