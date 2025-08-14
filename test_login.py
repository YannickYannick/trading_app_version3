#!/usr/bin/env python3
"""
Script pour tester la connexion et l'affichage des trades
"""

import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_trading_v3.settings.development')
django.setup()

from django.contrib.auth import authenticate, login
from django.test import RequestFactory
from trading_app.views import trade_tabulator
from django.contrib.auth.models import User

def test_login_and_trades():
    """Tester la connexion et l'affichage des trades"""
    print("🧪 Test de connexion et affichage des trades")
    print("=" * 50)
    
    # Créer une requête de test
    factory = RequestFactory()
    
    # Test avec différents utilisateurs
    test_users = ['Le-baff', 'test_user', 'admin']
    
    for username in test_users:
        try:
            user = User.objects.get(username=username)
            print(f"\n👤 Test avec l'utilisateur: {username}")
            
            # Créer une requête authentifiée
            request = factory.get('/trades/tabulator/')
            request.user = user
            
            # Appeler la vue
            response = trade_tabulator(request)
            
            if response.status_code == 200:
                print(f"✅ Vue appelée avec succès (status: {response.status_code})")
                
                # Vérifier le contexte
                if hasattr(response, 'context_data'):
                    context = response.context_data
                else:
                    context = getattr(response, 'context_data', {})
                
                if 'data_trades' in context:
                    data_trades = context['data_trades']
                    if data_trades and data_trades != '[]':
                        # Compter les trades dans le JSON
                        import json
                        try:
                            trades_list = json.loads(data_trades)
                            print(f"📊 Trades affichés: {len(trades_list)}")
                            
                            # Afficher quelques exemples
                            for i, trade in enumerate(trades_list[:2]):
                                symbol = trade.get('symbol', 'N/A')
                                direction = trade.get('direction', 'N/A')
                                size = trade.get('size', 'N/A')
                                platform = trade.get('platform', 'N/A')
                                print(f"    Trade {i+1}: {symbol} {direction} {size} ({platform})")
                                
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Erreur décodage JSON: {e}")
                    else:
                        print("⚠️ data_trades est vide")
                else:
                    print("❌ data_trades manquant dans le contexte")
                    print(f"🔍 Clés disponibles: {list(context.keys())}")
            else:
                print(f"❌ Erreur de la vue (status: {response.status_code})")
                
        except User.DoesNotExist:
            print(f"❌ Utilisateur {username} non trouvé")
        except Exception as e:
            print(f"❌ Erreur avec {username}: {e}")
    
    print("\n💡 Résumé:")
    print("   - 'Le-baff' devrait afficher 121 trades")
    print("   - 'test_user' devrait afficher 3 trades")
    print("   - 'admin' devrait afficher 0 trades")
    print("\n🔑 Pour voir les trades, connectez-vous avec l'utilisateur approprié !")

if __name__ == '__main__':
    test_login_and_trades()


















