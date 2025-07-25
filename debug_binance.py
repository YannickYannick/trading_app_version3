import pandas as pd
import sqlalchemy
from binance.client import Client
from binance import BinanceSocketManager
from pandas_datareader import data
from datetime import datetime, timedelta
from pandas_datareader import data as pdr_data
import yfinance as yf
from pprint import pprint

def debug_binance_account():
    """Fonction de debug pour voir ce que retourne l'API Binance"""
    
    # Tes credentials (attention, il faut les sécuriser !)
    api_key = "hE9jAjBCS9CVyxWof9gGok0pDqBC0TkaKZuZFS5pdrL2GVwrhhDu5NkjqN0rIMkW"
    api_secret = "JU6et8Jc1EuuyCNUduauipBixvCJMTqsoE113zyHXAYP65XgkWbIurc3hohmQR5n"
    
    try:
        client = Client(api_key, api_secret)
        
        # 1. Test de connexion
        print("=== TEST DE CONNEXION ===")
        server_time = client.get_server_time()
        print(f"Temps serveur: {server_time}")
        
        # 2. Récupération du compte
        print("\n=== RÉCUPÉRATION DU COMPTE ===")
        account = client.get_account()
        print(f"Type de réponse: {type(account)}")
        print(f"Clés disponibles: {list(account.keys())}")
        
        # 3. Vérification des balances
        print("\n=== VÉRIFICATION DES BALANCES ===")
        if 'balances' in account:
            balances = account['balances']
            print(f"Nombre total de balances: {len(balances)}")
            
            # Afficher les 5 premières balances pour voir la structure
            print("\nPremières 5 balances:")
            for i, balance in enumerate(balances[:5]):
                print(f"  {i+1}. {balance}")
            
            # Chercher spécifiquement EUR
            print("\n=== RECHERCHE EUR ===")
            eur_balances = [b for b in balances if b.get('asset') == 'EUR']
            print(f"Balances EUR trouvées: {len(eur_balances)}")
            for eur_balance in eur_balances:
                print(f"  EUR: {eur_balances}")
            
            # Filtrer les balances avec des fonds > 0
            print("\n=== BALANCES AVEC FONDS > 0 ===")
            balances_with_funds = [b for b in balances if float(b.get('free', 0)) > 0]
            print(f"Balances avec fonds > 0: {len(balances_with_funds)}")
            for balance in balances_with_funds:
                print(f"  {balance['asset']}: {balance['free']} (free) / {balance['locked']} (locked)")
                
        else:
            print("❌ Pas de 'balances' dans la réponse du compte")
            print("Réponse complète:")
            pprint(account)
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print(f"Type d'erreur: {type(e)}")

def get_positions_binance_fixed(start_date, stop_date):
    """Version corrigée de ta fonction"""
    api_key = "hE9jAjBCS9CVyxWof9gGok0pDqBC0TkaKZuZFS5pdrL2GVwrhhDu5NkjqN0rIMkW"
    api_secret = "JU6et8Jc1EuuyCNUduauipBixvCJMTqsoE113zyHXAYP65XgkWbIurc3hohmQR5n"
    
    try:
        client = Client(api_key, api_secret)
        all_actif_infos = []
        
        # Récupération sécurisée des balances
        account = client.get_account()
        if 'balances' not in account:
            print("❌ Pas de balances dans la réponse")
            return []
            
        balances = account['balances']
        
        # Filtrage avec gestion d'erreur
        list_actifs = []
        for balance in balances:
            try:
                free_amount = float(balance.get('free', 0))
                if free_amount > 0:
                    list_actifs.append(balance)
            except (ValueError, TypeError) as e:
                print(f"⚠️ Erreur avec balance {balance}: {e}")
                continue
        
        print(f"✅ {len(list_actifs)} actifs avec des fonds trouvés")
        
        for actif in list_actifs:
            actif_infos = {}
            
            actif_infos["1_ID"] = 111111
            actif_infos["2_name"] = actif["asset"]
            actif_infos["3_symbol"] = actif["asset"]
            actif_infos["4_quantity"] = actif['free']
            actif_infos["5_purchasePrice"] = "somme des transactions"
            actif_infos["6_date"] = "dernière date"
            
            print(f"\n--- Traitement de {actif['asset']} ---")
            print(f"Quantité: {actif['free']}")
            
            # Récupération des infos supplémentaires
            stock_more_infos = get_actif_infos(actif_infos["3_symbol"], start_date, stop_date)
            actif_infos.update(stock_more_infos)
            all_actif_infos.append(actif_infos)
        
        return all_actif_infos
        
    except Exception as e:
        print(f"❌ Erreur dans get_positions_binance_fixed: {e}")
        return []

def get_actif_infos(actif, start_date, stop_date):
    """Ta fonction get_actif_infos inchangée"""
    actif_infos = {} 
    
    if actif != "EUR":
        try:
            try:
                actif_name_modified = actif + "-EUR"
                asset_socket = data.get_quote_yahoo(actif_name_modified)
            except:
                actif_name_modified = actif + "-USD"
                asset_socket = data.get_quote_yahoo(actif_name_modified)

            actif_infos["7_currentValue"] = asset_socket['price'][0]        
            actif_infos["8_marketCap"] = asset_socket['marketCap'][0]*1E-9

            yf.pdr_override()
            stock_history = pdr_data.get_data_yahoo(actif_name_modified, start=start_date, end=stop_date)
            actif_infos["9_stock_history"] = stock_history
        
        except:
            try:
                actif_name_modified = actif + "-EUR"
                ticker = yf.Ticker(actif_name_modified)
                actif_infos["7_currentValue"] = round(ticker.history(period='1d')["Close"], 2)
                actif_infos["8_marketCap"] = ticker.info["marketCap"]
                actif_infos["9_stock_history"] = yf.download("BTC-USD", start=start_date, end=stop_date)
            except:
                actif_name_modified = actif + "-USD"
                ticker = yf.Ticker(actif_name_modified)
                actif_infos["7_currentValue"] = round(ticker.history(period='1d')["Close"], 2)
                actif_infos["8_marketCap"] = ticker.info["marketCap"]
                actif_infos["9_stock_history"] = yf.download(actif_name_modified, start=start_date, end=stop_date)
    
    return actif_infos

if __name__ == "__main__":
    print("🔍 DEBUG BINANCE API")
    print("=" * 50)
    
    # Test de debug
    debug_binance_account()
    
    print("\n" + "=" * 50)
    print("🧪 TEST FONCTION CORRIGÉE")
    
    # Test de la fonction corrigée
    start_date, stop_date = datetime.now() - timedelta(days=90), datetime.now()
    result = get_positions_binance_fixed(start_date, stop_date)
    
    print(f"\n✅ Résultat final: {len(result)} actifs traités")
    for actif in result:
        print(f"  - {actif['2_name']}: {actif['4_quantity']}") 