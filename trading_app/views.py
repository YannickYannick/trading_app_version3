from django.shortcuts import render
from .models import Asset, Trade, Position, Strategy, BrokerCredentials
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .services import BrokerService, SaxoAuthService
from .brokers.factory import BrokerFactory
from .models import AssetType, Market, AssetTradable
import requests
import yfinance as yf
from datetime import datetime, timedelta
from decimal import Decimal

# Create your views here.

def asset_list(request):
    assets = Asset.objects.all()
    return render(request, 'trading_app/asset_list.html', {'assets': assets})

def asset_tabulator(request):
    assets = Asset.objects.all().values()
    data_assets = list(assets)
    return render(request, 'trading_app/asset_tabulator.html', {
        'data_assets': json.dumps(data_assets, cls=DjangoJSONEncoder),
    })

#@csrf_exempt
def save_asset_ajax(request):
    if request.method == "POST":
        data = request.POST.dict() if request.POST else json.loads(request.body)
        symbol = data.get("symbol")
        if not symbol:
            return JsonResponse({"error": "No symbol provided"}, status=400)
        try:
            asset, created = Asset.objects.get_or_create(symbol=symbol)
            asset.name = data.get("name", asset.name)
            asset.type = data.get("type", asset.type)
            asset.platform = data.get("platform", asset.platform)
            # Conversion sécurisée pour les floats
            asset.last_price = float(data.get("last_price", asset.last_price) or 0)
            asset.is_active = str(data.get("is_active", asset.is_active)).lower() in ["true", "1"]
            asset.sector = data.get("sector", asset.sector)
            asset.industry = data.get("industry", asset.industry)
            asset.market_cap = float(data.get("market_cap", asset.market_cap) or 0)
            asset.price_history = data.get("price_history", asset.price_history)
            asset.data_source = data.get("data_source", asset.data_source)
            asset.id_from_platform = data.get("id_from_platform", asset.id_from_platform)
            asset.save()
            return JsonResponse({"success": True, "created": created})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)

def trade_tabulator(request):
    trades = Trade.objects.all().values()
    data_trades = list(trades)
    return render(request, 'trading_app/trade_tabulator.html', {
        'data_trades': json.dumps(data_trades, cls=DjangoJSONEncoder),
    })

def position_tabulator(request):
    positions = Position.objects.all().values()
    data_positions = list(positions)
    return render(request, 'trading_app/position_tabulator.html', {
        'data_positions': json.dumps(data_positions, cls=DjangoJSONEncoder),
    })

def strategy_tabulator(request):
    strategies = Strategy.objects.all().values()
    data_strategies = list(strategies)
    return render(request, 'trading_app/strategy_tabulator.html', {
        'data_strategies': json.dumps(data_strategies, cls=DjangoJSONEncoder),
    })

# Nouvelles vues pour les courtiers
@login_required
def broker_dashboard(request):
    """Tableau de bord des courtiers"""
    broker_service = BrokerService(request.user)
    user_brokers = broker_service.get_user_brokers()
    
    return render(request, 'trading_app/broker_dashboard.html', {
        'brokers': user_brokers,
        'supported_brokers': BrokerFactory.get_supported_brokers(),
    })

@login_required
def broker_config(request, broker_id=None):
    """Configuration d'un courtier"""
    broker = None
    if broker_id:
        try:
            broker = BrokerCredentials.objects.get(id=broker_id, user=request.user)
        except BrokerCredentials.DoesNotExist:
            pass
    
    if request.method == 'POST':
        broker_type = request.POST.get('broker_type')
        name = request.POST.get('name')
        
        if broker_type and name:
            if broker:
                # Mise à jour
                broker.broker_type = broker_type
                broker.name = name
                
                if broker_type == 'saxo':
                    broker.saxo_client_id = request.POST.get('saxo_client_id')
                    broker.saxo_client_secret = request.POST.get('saxo_client_secret')
                    broker.saxo_redirect_uri = request.POST.get('saxo_redirect_uri')
                    # Gestion des tokens manuels (optionnels)
                    access_token = request.POST.get('saxo_access_token')
                    refresh_token = request.POST.get('saxo_refresh_token')
                    if access_token:
                        broker.saxo_access_token = access_token
                    if refresh_token:
                        broker.saxo_refresh_token = refresh_token
                elif broker_type == 'binance':
                    broker.binance_api_key = request.POST.get('binance_api_key')
                    broker.binance_api_secret = request.POST.get('binance_api_secret')
                    broker.binance_testnet = request.POST.get('binance_testnet') == 'on'
                
                broker.save()
            else:
                # Création
                broker = BrokerCredentials.objects.create(
                    user=request.user,
                    broker_type=broker_type,
                    name=name,
                    saxo_client_id=request.POST.get('saxo_client_id'),
                    saxo_client_secret=request.POST.get('saxo_client_secret'),
                    saxo_redirect_uri=request.POST.get('saxo_redirect_uri'),
                    saxo_access_token=request.POST.get('saxo_access_token'),
                    saxo_refresh_token=request.POST.get('saxo_refresh_token'),
                    binance_api_key=request.POST.get('binance_api_key'),
                    binance_api_secret=request.POST.get('binance_api_secret'),
                    binance_testnet=request.POST.get('binance_testnet') == 'on',
                )
    
    return render(request, 'trading_app/broker_config.html', {
        'broker': broker,
        'supported_brokers': BrokerFactory.get_supported_brokers(),
    })

@login_required
def saxo_auth_callback(request):
    """Callback pour l'authentification Saxo"""
    code = request.GET.get('code')
    state = request.GET.get('state')
    
    if not code:
        return JsonResponse({"error": "Code d'autorisation manquant"}, status=400)
    
    # Récupérer les credentials Saxo de l'utilisateur
    try:
        broker_creds = BrokerCredentials.objects.filter(
            user=request.user, 
            broker_type='saxo',
            is_active=True
        ).first()
        
        if not broker_creds:
            return JsonResponse({"error": "Aucune configuration Saxo trouvée"}, status=400)
        
        # Utiliser le BrokerService pour l'authentification
        broker_service = BrokerService(request.user)
        success = broker_service.authenticate_saxo_with_code(broker_creds, code)
        
        if success:
            # Récupérer l'instance du broker pour sauvegarder les tokens
            broker = broker_service.get_broker_instance(broker_creds)
            
            # Sauvegarder les tokens dans les credentials
            broker_creds.saxo_access_token = broker.access_token
            broker_creds.saxo_refresh_token = broker.refresh_token
            broker_creds.saxo_token_expires_at = broker.token_expires_at
            broker_creds.save()
            
            return JsonResponse({"success": True, "message": "Authentification Saxo réussie"})
        else:
            return JsonResponse({"error": "Échec de l'authentification Saxo"}, status=400)
        
    except Exception as e:
        return JsonResponse({"error": f"Erreur d'authentification: {str(e)}"}, status=400)

@login_required
def saxo_auth_url(request):
    """Obtenir l'URL d'authentification Saxo"""
    try:
        broker_creds = BrokerCredentials.objects.filter(
            user=request.user, 
            broker_type='saxo',
            is_active=True
        ).first()
        
        if not broker_creds:
            return JsonResponse({"error": "Aucune configuration Saxo trouvée"}, status=400)
        
        broker_service = BrokerService(request.user)
        auth_url = broker_service.get_saxo_auth_url(broker_creds)
        
        return JsonResponse({
            "success": True,
            "auth_url": auth_url
        })
        
    except Exception as e:
        return JsonResponse({"error": f"Erreur: {str(e)}"}, status=400)

@login_required
@csrf_exempt
def sync_broker_data(request, broker_id):
    """Synchroniser les données depuis un courtier"""
    try:
        broker_creds = BrokerCredentials.objects.get(id=broker_id, user=request.user)
        broker_service = BrokerService(request.user)
        
        data_type = request.POST.get('data_type', 'positions')
        
        if data_type == 'positions':
            positions = broker_service.sync_positions_from_broker(broker_creds)
            return JsonResponse({
                "success": True,
                "message": f"{len(positions)} positions synchronisées"
            })
        elif data_type == 'trades':
            trades = broker_service.sync_trades_from_broker(broker_creds)
            return JsonResponse({
                "success": True,
                "message": f"{len(trades)} trades synchronisés"
            })
        else:
            return JsonResponse({"error": "Type de données non supporté"}, status=400)
            
    except BrokerCredentials.DoesNotExist:
        return JsonResponse({"error": "Courtier non trouvé"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"Erreur de synchronisation: {str(e)}"}, status=400)

@login_required
@csrf_exempt
def place_broker_order(request, broker_id):
    """Placer un ordre via un courtier"""
    try:
        broker_creds = BrokerCredentials.objects.get(id=broker_id, user=request.user)
        broker_service = BrokerService(request.user)
        
        data = json.loads(request.body)
        symbol = data.get('symbol')
        side = data.get('side')
        size = data.get('size')
        order_type = data.get('order_type', 'MARKET')
        price = data.get('price')
        
        if not all([symbol, side, size]):
            return JsonResponse({"error": "Paramètres manquants"}, status=400)
        
        result = broker_service.place_order(
            broker_creds,
            symbol,
            side,
            Decimal(str(size)),
            order_type,
            Decimal(str(price)) if price else None
        )
        
        return JsonResponse(result)
        
    except BrokerCredentials.DoesNotExist:
        return JsonResponse({"error": "Courtier non trouvé"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"Erreur de placement d'ordre: {str(e)}"}, status=400)

def test_broker_connection(request, broker_id):
    """Test de connexion à un broker spécifique"""
    try:
        credentials = BrokerCredentials.objects.get(id=broker_id, user=request.user)
        broker = BrokerFactory.create_broker(credentials.broker_type, request.user, credentials.get_credentials_dict())
        
        if credentials.broker_type == 'binance':
            # Test spécifique pour Binance
            test_result = broker.test_connection()
            auth_result = broker.authenticate()
            
            return JsonResponse({
                'success': True,
                'test_connection': test_result,
                'authentication': auth_result,
                'broker_type': credentials.broker_type,
                'base_url': broker.base_url if hasattr(broker, 'base_url') else 'N/A'
            })
        else:
            # Test générique pour autres brokers
            auth_result = broker.authenticate()
            return JsonResponse({
                'success': True,
                'authentication': auth_result,
                'broker_type': credentials.broker_type
            })
            
    except BrokerCredentials.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Broker non trouvé'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def asset_tradable_tabulator(request):
    """Vue pour gérer les AssetTradable avec Tabulator"""
    if request.method == 'POST':
        try:
            data = request.POST.dict()
            
            print(f"📝 Données reçues: {data}")
            
            # Récupérer le symbole
            symbol = data.get('symbol', '').upper().strip()
            
            if not symbol:
                return JsonResponse({'status': 'error', 'message': 'Le symbole ne peut pas être vide'})
            
            # Récupérer ou créer AssetType et Market
            asset_type, _ = AssetType.objects.get_or_create(name=data.get('asset_type', 'Unknown'))
            market, _ = Market.objects.get_or_create(name=data.get('market', 'Unknown'))
            
            # Récupérer les données Yahoo pour enrichir l'Asset
            yahoo_data = get_yahoo_data(symbol)
            
            if yahoo_data:
                print(f"✅ Données Yahoo trouvées pour {symbol}")
                # Utiliser les données Yahoo pour l'Asset
                asset_data = {
                    'symbol': symbol,
                    'name': yahoo_data.get('name', data.get('name', symbol)),
                    'sector': yahoo_data.get('sector', data.get('sector', 'xxxx')),
                    'industry': yahoo_data.get('industry', data.get('industry', 'xxxx')),
                    'market_cap': yahoo_data.get('market_cap', data.get('market_cap', 0.0)),
                    'price_history': yahoo_data.get('price_history', 'xxxx'),
                }
            else:
                print(f"⚠️ Pas de données Yahoo pour {symbol}, utilisation des données manuelles")
                asset_data = {
                    'symbol': symbol,
                    'name': data.get('name', symbol),
                    'sector': data.get('sector', 'xxxx'),
                    'industry': data.get('industry', 'xxxx'),
                    'market_cap': data.get('market_cap', 0.0),
                    'price_history': 'xxxx',
                }
            
            # Récupérer ou créer l'Asset sous-jacent
            asset, created = Asset.objects.get_or_create(
                symbol=symbol,
                defaults=asset_data
            )
            
            # Si l'Asset existe déjà, mettre à jour avec les données Yahoo
            if not created and yahoo_data:
                print(f"🔄 Mise à jour de l'Asset existant: {asset.symbol}")
                asset.name = asset_data['name']
                asset.sector = asset_data['sector']
                asset.industry = asset_data['industry']
                asset.market_cap = asset_data['market_cap']
                asset.save()
                print(f"✅ Asset mis à jour: {asset.symbol} - Secteur: {asset.sector} - Industrie: {asset.industry} - Market Cap: {asset.market_cap}")
            
            # Récupérer ou créer l'AssetTradable
            asset_tradable, created_tradable = AssetTradable.objects.get_or_create(
                symbol=symbol,
                platform=data.get('platform', 'saxo'),
                defaults={
                    'asset': asset,
                    'name': asset_data['name'],
                    'asset_type': asset_type,
                    'market': market,
                }
            )
            
            if not created_tradable:
                # Mise à jour si l'objet existe déjà
                asset_tradable.asset = asset
                asset_tradable.name = asset_data['name']
                asset_tradable.asset_type = asset_type
                asset_tradable.market = market
                asset_tradable.save()
            
            return JsonResponse({'status': 'success', 'message': 'AssetTradable sauvegardé'})
            
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde: {e}")
            return JsonResponse({'status': 'error', 'message': f'Erreur: {str(e)}'})
    
    # Récupérer les données pour Tabulator avec les informations de l'Asset
    asset_tradables = AssetTradable.objects.select_related('asset', 'asset_type', 'market').all()
    data_asset_tradables = []
    
    for at in asset_tradables:
        data_asset_tradables.append({
            'id': at.id,
            'asset_id': at.asset.id,
            'symbol': at.symbol,
            'name': at.name,
            'platform': at.platform,
            'asset_type': at.asset_type.name,
            'market': at.market.name,
            'sector': at.asset.sector,
            'industry': at.asset.industry,
            'market_cap': at.asset.market_cap,
            'created_at': at.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    
    return render(request, 'trading_app/asset_tradable_tabulator.html', {
        'data_asset_tradables': data_asset_tradables
    })

def asset_search_tabulator(request):
    """Vue pour rechercher et créer des AssetTradable"""
    if request.method == 'POST':
        try:
            data = request.POST.dict()
            symbol = data.get('symbol', '').upper()
            platform = data.get('platform', '')
            
            print(f" Recherche: {symbol} sur {platform}")
            
            if platform == 'saxo':
                # Recherche Saxo
                result = search_saxo_instrument(symbol)
                if result:
                    # Enrichir avec Yahoo Finance
                    yahoo_data = get_yahoo_data(symbol)
                    if yahoo_data:
                        result.update(yahoo_data)
                    
                    # Créer l'Asset et AssetTradable
                    asset, asset_tradable = create_asset_from_data(result, platform)
                    
                    return JsonResponse({
                        'status': 'success',
                        'message': f'AssetTradable créé: {asset_tradable.symbol}',
                        'data': {
                            'symbol': asset_tradable.symbol,
                            'name': asset_tradable.name,
                            'platform': asset_tradable.platform,
                            'asset_type': asset_tradable.asset_type.name,
                            'market': asset_tradable.market.name,
                            'sector': asset.sector,
                            'industry': asset.industry,
                            'market_cap': asset.market_cap,
                        }
                    })
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Symbole {symbol} non trouvé sur Saxo'
                    })
            
            elif platform == 'yahoo':
                # Recherche Yahoo Finance uniquement
                yahoo_data = get_yahoo_data(symbol)
                if yahoo_data:
                    # Créer l'Asset et AssetTradable
                    asset, asset_tradable = create_asset_from_data(yahoo_data, platform)
                    
                    return JsonResponse({
                        'status': 'success',
                        'message': f'AssetTradable créé: {asset_tradable.symbol}',
                        'data': {
                            'symbol': asset_tradable.symbol,
                            'name': asset_tradable.name,
                            'platform': asset_tradable.platform,
                            'asset_type': asset_tradable.asset_type.name,
                            'market': asset_tradable.market.name,
                            'sector': asset.sector,
                            'industry': asset.industry,
                            'market_cap': asset.market_cap,
                        }
                    })
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Symbole {symbol} non trouvé sur Yahoo Finance'
                    })
            
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Plateforme {platform} non supportée'
                })
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Erreur: {str(e)}'
            })
    
    # Récupérer les AssetTradable existants pour l'affichage
    asset_tradables = AssetTradable.objects.select_related('asset', 'asset_type', 'market').all()
    data_asset_tradables = []
    
    for at in asset_tradables:
        data_asset_tradables.append({
            'id': at.id,
            'symbol': at.symbol,
            'name': at.name,
            'platform': at.platform,
            'asset_type': at.asset_type.name,
            'market': at.market.name,
            'sector': at.asset.sector,
            'industry': at.asset.industry,
            'market_cap': at.asset.market_cap,
            'created_at': at.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    
    return render(request, 'trading_app/asset_search_tabulator.html', {
        'data_asset_tradables': data_asset_tradables
    })

def search_saxo_instrument(symbol: str) -> dict:
    """Recherche un instrument sur Saxo Bank"""
    try:
        # Récupérer le token Saxo (à adapter selon ta logique d'authentification)
        from .models import BrokerCredentials
        credentials = BrokerCredentials.objects.filter(broker_type='saxo').first()
        
        if not credentials or not credentials.saxo_access_token:
            print("❌ Pas de token Saxo disponible")
            return None
        
        headers = {"Authorization": f"Bearer {credentials.saxo_access_token}"}
        search_url = "https://gateway.saxobank.com/sim/openapi/ref/v1/instruments"
        params = {"Keyword": symbol, "AssetTypes": "Stock"}
        
        print(f"🌐 Recherche Saxo: {search_url} avec {params}")
        response = requests.get(search_url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Chercher l'instrument exact
            for instrument in data.get("Data", []):
                if instrument.get("Symbol") == f"{symbol}:xnas":
                    print(f"✅ Instrument trouvé: {instrument}")
                    return {
                        'symbol': symbol,
                        'name': instrument.get("Description", symbol),
                        'type': 'Stock',
                        'market': instrument.get("ExchangeId", "NASDAQ"),
                        'sector': 'Unknown',
                        'industry': 'Unknown',
                        'market_cap': 0.0,
                        'price_history': 'xxxx',
                        'saxo_identifier': instrument.get("Identifier"),
                        'saxo_exchange_id': instrument.get("ExchangeId"),
                    }
            
            print(f"❌ Symbole {symbol} non trouvé dans la réponse Saxo")
            return None
        else:
            print(f"❌ Erreur API Saxo: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Erreur recherche Saxo: {e}")
        return None

def get_yahoo_data(symbol: str) -> dict:
    """Récupère les données depuis Yahoo Finance"""
    try:
        # Vérifier que le symbole n'est pas vide
        if not symbol or symbol.strip() == "":
            print(f"⚠️ Symbole vide, pas de recherche Yahoo")
            return None
            
        print(f"📈 Recherche Yahoo Finance pour: {symbol}")
        
        # Nettoyer le symbole (enlever les suffixes de marché si nécessaire)
        clean_symbol = symbol.split(':')[0] if ':' in symbol else symbol
        clean_symbol = clean_symbol.strip()  # Enlever les espaces
        
        if not clean_symbol:
            print(f"⚠️ Symbole nettoyé vide")
            return None
            
        print(f" Symbole nettoyé: {clean_symbol}")
        
        ticker = yf.Ticker(clean_symbol)
        
        # Prix actuel
        hist = ticker.history(period="1d")
        current_price = hist["Close"].iloc[-1] if not hist.empty else 0.0
        print(f"💰 Prix actuel: {current_price}")
        
        # Métadonnées
        info = ticker.info
        print(f"📋 Info disponibles: {list(info.keys())}")
        
        # Gérer les cas où les données sont manquantes
        market_cap = info.get("marketCap", 0.0)
        if market_cap == "N/A" or market_cap is None:
            market_cap = 0.0
            
        sector = info.get("sector", "Unknown")
        if sector == "N/A" or sector is None:
            sector = "Unknown"
            
        industry = info.get("industry", "Unknown")
        if industry == "N/A" or industry is None:
            industry = "Unknown"
            
        name = info.get("longName", symbol)
        if name == "N/A" or name is None:
            name = symbol
        
        print(f"✅ Données Yahoo récupérées:")
        print(f"   - Nom: {name}")
        print(f"   - Prix: {current_price}")
        print(f"   - Secteur: {sector}")
        print(f"   - Industrie: {industry}")
        print(f"   - Market Cap: {market_cap}")
        
        return {
            'symbol': symbol,
            'name': name,
            'type': 'Stock',
            'market': 'Yahoo',
            'sector': sector,
            'industry': industry,
            'market_cap': market_cap,
            'price_history': 'xxxx',
            'current_price': current_price,
        }
        
    except Exception as e:
        print(f"❌ Erreur Yahoo Finance pour {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_asset_from_data(data: dict, platform: str) -> tuple:
    """Crée un Asset et AssetTradable à partir des données"""
    try:
        # Récupérer ou créer AssetType et Market
        asset_type, _ = AssetType.objects.get_or_create(name=data.get('type', 'Unknown'))
        market, _ = Market.objects.get_or_create(name=data.get('market', 'Unknown'))
        
        # Récupérer ou créer l'Asset sous-jacent
        asset, created = Asset.objects.get_or_create(
            symbol=data['symbol'],
            defaults={
                'name': data.get('name', data['symbol']),
                'sector': data.get('sector', 'xxxx'),
                'industry': data.get('industry', 'xxxx'),
                'market_cap': data.get('market_cap', 0.0),
                'price_history': data.get('price_history', 'xxxx'),
            }
        )
        
        # Si l'Asset existe déjà, mettre à jour avec les nouvelles données Yahoo
        if not created:
            print(f"🔄 Mise à jour de l'Asset existant: {asset.symbol}")
            asset.name = data.get('name', asset.name)
            asset.sector = data.get('sector', asset.sector)
            asset.industry = data.get('industry', asset.industry)
            asset.market_cap = data.get('market_cap', asset.market_cap)
            asset.save()
            print(f"✅ Asset mis à jour: {asset.symbol} - Secteur: {asset.sector} - Industrie: {asset.industry} - Market Cap: {asset.market_cap}")
        
        # Récupérer ou créer l'AssetTradable
        asset_tradable, created_tradable = AssetTradable.objects.get_or_create(
            symbol=data['symbol'],
            platform=platform,
            defaults={
                'asset': asset,
                'name': data.get('name', data['symbol']),
                'asset_type': asset_type,
                'market': market,
            }
        )
        
        # Si l'AssetTradable existe déjà, mettre à jour
        if not created_tradable:
            print(f"🔄 Mise à jour de l'AssetTradable existant: {asset_tradable.symbol}")
            asset_tradable.asset = asset
            asset_tradable.name = data.get('name', asset_tradable.name)
            asset_tradable.asset_type = asset_type
            asset_tradable.market = market
            asset_tradable.save()
        
        print(f"✅ AssetTradable créé/mis à jour: {asset_tradable.symbol} sur {platform}")
        return asset, asset_tradable
        
    except Exception as e:
        print(f"❌ Erreur création AssetTradable: {e}")
        raise

def update_all_assets_with_yahoo(request):
    """Met à jour tous les Assets existants avec les données Yahoo Finance"""
    if request.method == 'POST':
        try:
            assets = Asset.objects.all()
            updated_count = 0
            
            for asset in assets:
                try:
                    print(f"📈 Mise à jour de {asset.symbol}...")
                    
                    # Récupérer les données Yahoo
                    yahoo_data = get_yahoo_data(asset.symbol)
                    
                    if yahoo_data:
                        # Mettre à jour l'Asset
                        asset.name = yahoo_data.get('name', asset.name)
                        asset.sector = yahoo_data.get('sector', asset.sector)
                        asset.industry = yahoo_data.get('industry', asset.industry)
                        asset.market_cap = yahoo_data.get('market_cap', asset.market_cap)
                        asset.save()
                        
                        updated_count += 1
                        print(f"✅ {asset.symbol} mis à jour: {asset.sector} - {asset.industry} - {asset.market_cap}")
                    else:
                        print(f"⚠️ Pas de données Yahoo pour {asset.symbol}")
                        
                except Exception as e:
                    print(f"❌ Erreur mise à jour {asset.symbol}: {e}")
                    continue
            
            return JsonResponse({
                'status': 'success',
                'message': f'{updated_count} Assets mis à jour avec succès'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Erreur: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'})

def place_order_view(request):
    """Vue pour passer des ordres d'achat/vente"""
    if request.method == 'POST':
        try:
            data = request.POST.dict()
            
            asset_tradable_id = data.get('asset_tradable_id')
            amount = float(data.get('amount', 0))
            side = data.get('side', 'Buy')  # Buy ou Sell
            broker_type = data.get('broker_type', 'saxo')
            
            print(f" Ordre reçu: {asset_tradable_id} - {amount} - {side} - {broker_type}")
            
            if broker_type == 'saxo':
                result = place_saxo_order(asset_tradable_id, amount, side)
            elif broker_type == 'binance':
                result = place_binance_order(asset_tradable_id, amount, side)
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Broker {broker_type} non supporté'
                })
            
            return JsonResponse(result)
            
        except Exception as e:
            print(f"❌ Erreur lors du passage d'ordre: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Erreur: {str(e)}'
            })
    
    # Récupérer les AssetTradable pour le formulaire
    asset_tradables = AssetTradable.objects.select_related('asset', 'asset_type', 'market').all()
    
    return render(request, 'trading_app/place_order.html', {
        'asset_tradables': asset_tradables
    })

def place_saxo_order(asset_tradable_id: int, amount: float, side: str) -> dict:
    """Passe un ordre sur Saxo Bank"""
    try:
        print(f"🔐 Passage d'ordre Saxo: {asset_tradable_id} - {amount} - {side}")
        
        # Récupérer l'AssetTradable
        asset_tradable = AssetTradable.objects.get(id=asset_tradable_id)
        
        # Récupérer les credentials Saxo
        credentials = BrokerCredentials.objects.filter(broker_type='saxo').first()
        
        if not credentials or not credentials.saxo_access_token:
            return {
                'status': 'error',
                'message': 'Pas de token Saxo disponible'
            }
        
        # Authentifier
        headers = {
            "Authorization": f"Bearer {credentials.saxo_access_token}",
            "Content-Type": "application/json"
        }
        
        # Récupérer l'AccountKey
        accounts_url = "https://gateway.saxobank.com/sim/openapi/port/v1/accounts/me"
        accounts_response = requests.get(accounts_url, headers=headers)
        
        if accounts_response.status_code != 200:
            return {
                'status': 'error',
                'message': f'Erreur récupération comptes: {accounts_response.status_code}'
            }
        
        accounts_data = accounts_response.json()
        accounts = accounts_data.get("Data", [])
        
        if not accounts:
            return {
                'status': 'error',
                'message': 'Aucun compte trouvé'
            }
        
        account_key = accounts[0].get("AccountKey")
        print(f"✅ AccountKey récupéré: {account_key}")
        
        # Récupérer l'UIC depuis l'AssetTradable
        # Pour l'instant, on utilise un UIC par défaut (à adapter selon ta logique)
        uic = 211  # À remplacer par la vraie logique de récupération UIC
        
        # Préparer l'ordre
        order_payload = {
            "AccountKey": account_key,
            "Uic": uic,
            "AssetType": "Stock",  # <-- FORCE ici la valeur "Stock"
            "OrderType": "Market",
            "BuySell": side,
            "Amount": int(amount),
            "ManualOrder": True,
            "OrderDuration": {
                "DurationType": "DayOrder"
            }
        }
        
        print(f"📋 Payload ordre: {order_payload}")
        
        # Passer l'ordre
        order_url = "https://gateway.saxobank.com/sim/openapi/trade/v2/orders"
        order_response = requests.post(order_url, headers=headers, json=order_payload)
        
        print(f"📊 Réponse ordre: {order_response.status_code} - {order_response.text}")
        
        if order_response.status_code == 200:
            order_data = order_response.json()
            return {
                'status': 'success',
                'message': f'Ordre passé avec succès: {order_data}',
                'order_id': order_data.get('OrderId', 'Unknown')
            }
        else:
            return {
                'status': 'error',
                'message': f'Erreur passage ordre: {order_response.status_code} - {order_response.text}'
            }
            
    except Exception as e:
        print(f"❌ Erreur passage ordre Saxo: {e}")
        return {
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }

def place_binance_order(asset_tradable_id: int, amount: float, side: str) -> dict:
    """Passe un ordre sur Binance"""
    try:
        print(f"🔐 Passage d'ordre Binance: {asset_tradable_id} - {amount} - {side}")
        
        # Récupérer l'AssetTradable
        asset_tradable = AssetTradable.objects.get(id=asset_tradable_id)
        
        # Récupérer les credentials Binance
        credentials = BrokerCredentials.objects.filter(broker_type='binance').first()
        
        if not credentials or not credentials.binance_api_key or not credentials.binance_api_secret:
            return {
                'status': 'error',
                'message': 'Pas de credentials Binance disponibles'
            }
        
        # Créer le broker Binance
        from .brokers.binance import BinanceBroker
        broker = BinanceBroker(credentials.binance_api_key, credentials.binance_api_secret)
        
        if not broker.authenticate():
            return {
                'status': 'error',
                'message': 'Échec authentification Binance'
            }
        
        # Passer l'ordre (à implémenter dans BinanceBroker)
        # result = broker.place_order(asset_tradable.symbol, amount, side)
        
        return {
            'status': 'success',
            'message': 'Ordre Binance passé avec succès (à implémenter)'
        }
        
    except Exception as e:
        print(f"❌ Erreur passage ordre Binance: {e}")
        return {
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }

