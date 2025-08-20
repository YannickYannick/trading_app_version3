#!/usr/bin/env python3
"""
Script de debug pour diagnostiquer le problème de refresh token Saxo Bank
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings')
django.setup()

from trading_app.models import BrokerCredentials, User
from trading_app.brokers.saxo import SaxoBroker
from trading_app.services import BrokerService

def debug_saxo_refresh():
    """Debug complet du refresh token Saxo"""
    
    print("🔍 DEBUG COMPLET REFRESH TOKEN SAXO BANK")
    print("=" * 60)
    
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
        print(f"   Access Token: {'✅ Présent' if cred.saxo_access_token else '❌ Absent'}")
        print(f"   Refresh Token: {'✅ Présent' if cred.saxo_refresh_token else '❌ Absent'}")
        print(f"   Expire le: {cred.saxo_token_expires_at}")
        
        if cred.saxo_access_token and cred.saxo_refresh_token:
            print(f"   Tokens identiques: {'⚠️ OUI (Token 24h)' if cred.saxo_access_token == cred.saxo_refresh_token else '✅ NON (Refresh possible)'}")
        
        # 3. Tester la connectivité
        print(f"\n🔌 Test de connectivité pour {cred.name}...")
        try:
            # Créer l'instance du broker
            broker = SaxoBroker(cred.user, {
                'client_id': cred.saxo_client_id,
                'client_secret': cred.saxo_client_secret,
                'redirect_uri': cred.saxo_redirect_uri,
                'environment': getattr(cred, 'saxo_environment', 'simulation'),
                'access_token': cred.saxo_access_token,
                'refresh_token': cred.saxo_refresh_token,
                'token_expires_at': cred.saxo_token_expires_at
            })
            
            # Test de connectivité
            connectivity = broker.test_connectivity()
            print("   📡 Résultats connectivité:")
            for endpoint, result in connectivity.items():
                status = "✅" if result.get('success') else "❌"
                print(f"      {status} {endpoint}: {result.get('message', 'N/A')}")
            
            # Vérifier le statut du token
            token_status = broker.check_token_status()
            print(f"   🔑 Statut du token:")
            print(f"      Valide: {'✅' if token_status.get('valid') else '❌'}")
            print(f"      Message: {token_status.get('message', 'N/A')}")
            print(f"      Expire dans: {token_status.get('expires_in', 'N/A')}")
            
            # 4. Tenter le refresh si possible
            if (broker.refresh_token and 
                broker.refresh_token != broker.access_token and
                not broker.is_24h_token()):
                
                print(f"\n🔄 Tentative de refresh du token...")
                print(f"   Refresh Token: {broker.refresh_token[:20]}...")
                print(f"   Access Token actuel: {broker.access_token[:20]}...")
                
                # Test de refresh avec logs détaillés
                refresh_success = broker.refresh_auth_token()
                
                if refresh_success:
                    print("   ✅ Refresh réussi !")
                    print(f"   Nouveau Access Token: {broker.access_token[:20]}...")
                    print(f"   Nouveau Refresh Token: {broker.refresh_token[:20]}...")
                    print(f"   Nouvelle expiration: {broker.token_expires_at}")
                    
                    # Mettre à jour la base de données
                    cred.saxo_access_token = broker.access_token
                    cred.saxo_refresh_token = broker.refresh_token
                    cred.saxo_token_expires_at = broker.token_expires_at
                    cred.save()
                    print("   💾 Tokens mis à jour dans la base de données")
                else:
                    print("   ❌ Refresh échoué")
            else:
                if broker.is_24h_token():
                    print(f"   ⚠️ Token 24h détecté - pas de refresh possible")
                else:
                    print(f"   ⚠️ Refresh token non disponible ou identique à l'access token")
            
        except Exception as e:
            print(f"   ❌ Erreur lors du test: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🏁 Debug terminé")

def test_specific_broker(broker_id):
    """Tester un broker spécifique"""
    try:
        cred = BrokerCredentials.objects.get(id=broker_id, broker_type='saxo')
        print(f"🔍 Test spécifique du broker {cred.name} (ID: {broker_id})")
        
        # Créer l'instance du broker
        broker = SaxoBroker(cred.user, {
            'client_id': cred.saxo_client_id,
            'client_secret': cred.saxo_client_secret,
            'redirect_uri': cred.saxo_redirect_uri,
            'environment': getattr(cred, 'saxo_environment', 'simulation'),
            'access_token': cred.saxo_access_token,
            'refresh_token': cred.saxo_refresh_token,
            'token_expires_at': cred.saxo_token_expires_at
        })
        
        # Test de refresh détaillé
        print(f"\n🔄 Test de refresh détaillé:")
        print(f"   URL d'auth: {broker.auth_url}")
        print(f"   URL de base: {broker.base_url}")
        print(f"   Client ID: {broker.client_id}")
        print(f"   Access Token: {broker.access_token[:20] if broker.access_token else 'None'}...")
        print(f"   Refresh Token: {broker.refresh_token[:20] if broker.refresh_token else 'None'}...")
        print(f"   Token 24h: {'Oui' if broker.is_24h_token() else 'Non'}")
        
        if broker.refresh_token and not broker.is_24h_token():
            print(f"\n🔄 Tentative de refresh...")
            success = broker.refresh_auth_token()
            print(f"   Résultat: {'✅ Succès' if success else '❌ Échec'}")
            
            if success:
                print(f"   Nouveau Access Token: {broker.access_token[:20]}...")
                print(f"   Nouveau Refresh Token: {broker.refresh_token[:20]}...")
                print(f"   Nouvelle expiration: {broker.token_expires_at}")
        else:
            print(f"   ⚠️ Refresh non possible")
            
    except BrokerCredentials.DoesNotExist:
        print(f"❌ Broker ID {broker_id} non trouvé")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test d'un broker spécifique
        try:
            broker_id = int(sys.argv[1])
            test_specific_broker(broker_id)
        except ValueError:
            print("❌ L'ID du broker doit être un nombre")
    else:
        # Debug complet
        debug_saxo_refresh()
