from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from django.urls import reverse
from django.conf import settings
from decimal import Decimal
import json
import logging
from datetime import datetime, timedelta
from .services import BrokerService
import requests
import yfinance as yf
from django.core.serializers.json import DjangoJSONEncoder
from .brokers.factory import BrokerFactory
from .models import Asset, Position, Trade, Strategy, BrokerCredentials, AssetType, Market, AssetTradable

logger = logging.getLogger(__name__)

def home(request):
    """Page d'accueil de l'application de trading"""
    context = {
        'total_assets': Asset.objects.count(),
        'total_positions': Position.objects.count(),
        'total_trades': Trade.objects.count(),
        'total_strategies': Strategy.objects.count(),
        'total_brokers': BrokerCredentials.objects.count(),
    }
    return render(request, 'home.html', context)

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
    """Vue pour afficher les trades dans un tableau Tabulator"""
    # Charger uniquement les trades depuis la base de données
    trades = Trade.objects.all().order_by('-timestamp')[:100]  # Limite à 100 trades
    
    print(f"🔍 {trades.count()} trades trouvés en base de données")
    
    # Formater les données pour Tabulator
    tabledata = [{
        'id': trade.id,
        'symbol': trade.asset_tradable.symbol if trade.asset_tradable else 'N/A',
        'direction': trade.side,
        'size': float(trade.size),
        'opening_price': float(trade.price),
        'closing_price': float(trade.price),  # Même prix pour l'instant
        'profit_loss': 0,  # À calculer si nécessaire
        'profit_loss_ratio': 0,
        'opening_date': trade.timestamp.strftime('%Y-%m-%d'),
        'timestamp': trade.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'broker_name': trade.platform,
    } for trade in trades]

    print(f"📊 {len(tabledata)} trades formatés pour l'affichage")

    return render(request, 'trading_app/trade_tabulator.html', {
        'data_trades': json.dumps(tabledata, cls=DjangoJSONEncoder)
    })
def trade_tabulator_with_synch(request):
    """Affiche les trades depuis les brokers"""
    from .brokers.factory import BrokerFactory
    from .models import BrokerCredentials
    
    all_trades = []
    
    # Récupérer tous les brokers configurés
    brokers = BrokerCredentials.objects.filter(is_active=True)
    
    for broker in brokers:
        try:
            credentials = broker.get_credentials_dict()
            broker_instance = BrokerFactory.create_broker(broker.broker_type, None, credentials)
            
            if hasattr(broker_instance, "get_trades"):
                trades = broker_instance.get_trades(limit=50)
                
                # Ajouter les informations du broker à chaque trade
                for trade in trades:
                    trade['broker_name'] = broker.name
                    trade['broker_type'] = broker.broker_type
                    trade['environment'] = broker.environment
                
                all_trades.extend(trades)
                print(f"✅ {len(trades)} trades récupérés depuis {broker.name}")
            else:
                print(f"⚠️ Broker {broker.name} n'a pas de méthode get_trades")
                
        except Exception as e:
            print(f"❌ Erreur récupération trades pour {broker.name}: {e}")
            continue
    
    print(f"📊 Total: {len(all_trades)} trades récupérés")
    
    return render(request, 'trading_app/trade_tabulator.html', {
        'data_trades': json.dumps(all_trades, cls=DjangoJSONEncoder),
    })

def position_tabulator(request):
    positions = Position.objects.select_related('asset_tradable__asset').all()
    data_positions = []
    for position in positions:
        position_data = {
            'id': position.id,
            'user_id': position.user_id,
            'asset_tradable_id': position.asset_tradable_id,
            'asset_name': position.asset_tradable.name,
            'asset_symbol': position.asset_tradable.symbol,
            'underlying_asset_name': position.asset_tradable.asset.name,
            'underlying_asset_symbol': position.asset_tradable.asset.symbol,
            'size': str(position.size),
            'entry_price': str(position.entry_price),
            'current_price': str(position.current_price),
            'side': position.side,
            'status': position.status,
            'pnl': str(position.pnl),
            'created_at': position.created_at.isoformat(),
            'updated_at': position.updated_at.isoformat(),
        }
        data_positions.append(position_data)
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
    broker_balances = {}
    from .brokers.factory import BrokerFactory
    for broker in user_brokers:
        credentials = broker.get_credentials_dict()
        broker_instance = BrokerFactory.create_broker(broker.broker_type, request.user, credentials)
        if hasattr(broker_instance, "get_balance"):
            broker_balances[broker.id] = broker_instance.get_balance()
        else:
            broker_balances[broker.id] = None
    return render(request, 'trading_app/broker_dashboard.html', {
        'brokers': user_brokers,
        'supported_brokers': BrokerFactory.get_supported_brokers(),
        'broker_balances': broker_balances,
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
                broker.environment = request.POST.get('environment', 'simulation')
                
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
                    environment=request.POST.get('environment', 'simulation'),
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

def get_saxo_instrument_details(uic: int, asset_type: str = "Stock") -> dict:
    """Récupère les détails d'un instrument Saxo par UIC"""
    try:
        from .models import BrokerCredentials
        from .brokers.factory import BrokerFactory
        
        # Récupérer les credentials Saxo
        credentials_obj = BrokerCredentials.objects.filter(broker_type='saxo').first()
        if not credentials_obj:
            print("❌ Pas de credentials Saxo trouvés")
            return None
        
        credentials = credentials_obj.get_credentials_dict()
        broker = BrokerFactory.create_broker('saxo', None, credentials)
        
        if not broker.authenticate():
            print("❌ Échec de l'authentification Saxo")
            return None
        
        # Construire l'URL pour les détails de l'instrument
        base_url = broker.base_url
        url = f"{base_url}/ref/v1/instruments/details/{uic}/{asset_type.lower()}"
        
        headers = {
            "Authorization": f"Bearer {broker.access_token}",
            "Accept": "application/json"
        }
        
        print(f"🌐 Appel API Saxo: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Réponse Saxo: {data}")
            
            return {
                'description': data.get("Description"),
                'symbol': data.get("Symbol"),
                'identifier': data.get("Identifier"),
                'exchange_id': data.get("ExchangeId"),
                'asset_type': data.get("AssetType"),
            }
        else:
            print(f"❌ Erreur API Saxo: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Erreur récupération détails Saxo: {e}")
        return None

def update_asset_tradable_from_saxo(asset_tradable_id: int) -> bool:
    """Met à jour un AssetTradable avec les informations Saxo"""
    try:
        from .models import AssetTradable
        
        asset_tradable = AssetTradable.objects.get(id=asset_tradable_id)
        
        # Récupérer les détails depuis Saxo
        details = get_saxo_instrument_details(asset_tradable.symbol, asset_tradable.asset_type.name)
        
        if details:
            # Mettre à jour l'AssetTradable
            asset_tradable.name = details.get('description', asset_tradable.name)
            asset_tradable.symbol = details.get('symbol', asset_tradable.symbol)
            asset_tradable.save()
            
            print(f"✅ AssetTradable {asset_tradable_id} mis à jour: {asset_tradable.name} ({asset_tradable.symbol})")
            return True
        else:
            print(f"❌ Impossible de récupérer les détails pour AssetTradable {asset_tradable_id}")
            return False
            
    except AssetTradable.DoesNotExist:
        print(f"❌ AssetTradable {asset_tradable_id} non trouvé")
        return False
    except Exception as e:
        print(f"❌ Erreur mise à jour AssetTradable: {e}")
        return False

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

@login_required
def update_asset_tradable_saxo(request, asset_tradable_id):
    """Met à jour un AssetTradable avec les informations Saxo"""
    if request.method == 'POST':
        success = update_asset_tradable_from_saxo(asset_tradable_id)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'AssetTradable mis à jour avec succès'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Erreur lors de la mise à jour'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@login_required
def update_all_saxo_assets(request):
    """Met à jour tous les AssetTradable Saxo avec les informations de l'API"""
    if request.method == 'POST':
        from .models import AssetTradable
        
        saxo_assets = AssetTradable.objects.filter(platform='saxo')
        updated_count = 0
        error_count = 0
        
        for asset in saxo_assets:
            try:
                if update_asset_tradable_from_saxo(asset.id):
                    updated_count += 1
                else:
                    error_count += 1
            except Exception as e:
                print(f"❌ Erreur mise à jour asset {asset.id}: {e}")
                error_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'{updated_count} AssetTradable Saxo mis à jour, {error_count} erreurs'
        })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@login_required
def update_saxo_assets_page(request):
    """Page pour mettre à jour les AssetTradable Saxo"""
    return render(request, 'trading_app/update_saxo_assets.html')

@csrf_exempt
@require_http_methods(["POST"])
def binance_trades_ajax(request):
    """Vue AJAX pour récupérer les trades Binance selon le mode et sauvegarder uniquement les nouvelles données"""
    try:
        data = json.loads(request.body)
        mode = data.get('mode', 'auto')
        
        from .brokers.factory import BrokerFactory
        from .models import BrokerCredentials, Trade, AssetTradable, Asset, AssetType, Market
        
        # Récupérer les credentials Binance
        binance_credentials = BrokerCredentials.objects.filter(
            broker_type='binance', 
            is_active=True
        ).first()
        
        if not binance_credentials:
            return JsonResponse({
                'success': False,
                'error': 'Aucune configuration Binance active trouvée'
            })
        
        # Créer l'instance Binance
        credentials = binance_credentials.get_credentials_dict()
        binance_broker = BrokerFactory.create_broker('binance', request.user, credentials)
        
        # Récupérer les trades selon le mode
        trades_data = binance_broker.get_trades(limit=1000, mode=mode)
        
        print(f"🔍 {len(trades_data)} trades récupérés depuis Binance (mode: {mode})")
        
        # Récupérer les trades existants en base pour comparaison
        existing_trades = Trade.objects.filter(
            user=request.user,
            platform='binance'
        ).select_related('asset_tradable').values_list('timestamp', 'asset_tradable__symbol', 'side', 'size', 'price')
        
        print(f"📊 {len(existing_trades)} trades existants en base de données")
        
        # Créer un set des trades existants pour comparaison rapide
        existing_trades_set = set()
        for trade in existing_trades:
            timestamp, symbol, side, size, price = trade
            # Créer une clé unique pour chaque trade
            trade_key = (timestamp, symbol, side, float(size), float(price))
            existing_trades_set.add(trade_key)
        
        print(f"🔑 {len(existing_trades_set)} clés uniques créées pour comparaison")
        
        # Sauvegarder uniquement les nouveaux trades
        saved_count = 0
        for trade_data in trades_data:
            try:
                # Créer ou récupérer l'Asset si nécessaire
                symbol = trade_data.get('symbol', 'N/A')
                asset, created = Asset.objects.get_or_create(
                    symbol=symbol,
                    defaults={
                        'name': symbol,
                        'sector': 'Cryptocurrency',
                        'industry': 'Digital Assets',
                        'market_cap': 0.0,
                        'price_history': 'xxxx'
                    }
                )
                
                # Créer ou récupérer AssetType et Market pour Binance
                asset_type, _ = AssetType.objects.get_or_create(name='Crypto')
                market, _ = Market.objects.get_or_create(name='Binance')
                
                # Créer ou récupérer AssetTradable
                asset_tradable, created = AssetTradable.objects.get_or_create(
                    symbol=symbol,
                    platform='binance',
                    defaults={
                        'asset': asset,
                        'name': symbol,
                        'asset_type': asset_type,
                        'market': market
                    }
                )
                
                # Préparer les données du trade
                trade_timestamp = datetime.strptime(trade_data.get('timestamp', ''), '%Y-%m-%d %H:%M:%S')
                trade_size = trade_data.get('size', 0)
                trade_price = trade_data.get('opening_price', 0)
                trade_side = trade_data.get('direction', 'BUY')
                
                # Créer la clé unique pour ce trade
                trade_key = (trade_timestamp, symbol, trade_side, float(trade_size), float(trade_price))
                
                # Vérifier si ce trade existe déjà
                if trade_key not in existing_trades_set:
                    # Créer le nouveau Trade
                    trade = Trade.objects.create(
                        user=request.user,
                        asset_tradable=asset_tradable,
                        size=trade_size,
                        price=trade_price,
                        side=trade_side,
                        timestamp=trade_timestamp,
                        platform='binance'
                    )
                    saved_count += 1
                    print(f"✅ Nouveau trade sauvegardé: {symbol} {trade_side} {trade_size} @ {trade_price}")
                else:
                    print(f"⏭️ Trade déjà existant: {symbol} {trade_side} {trade_size} @ {trade_price}")
                    
            except Exception as e:
                print(f"❌ Erreur sauvegarde trade {trade_data.get('symbol', 'N/A')}: {e}")
                continue
        
        # Récupérer tous les trades sauvegardés pour l'affichage (pas seulement les nouveaux)
        saved_trades = Trade.objects.filter(user=request.user).order_by('-timestamp')[:100]
        
        # Formater pour Tabulator
        formatted_trades = [{
            'id': trade.id,
            'symbol': trade.asset_tradable.symbol if trade.asset_tradable else 'N/A',
            'direction': trade.side,
            'size': float(trade.size),
            'opening_price': float(trade.price),
            'closing_price': float(trade.price),
            'profit_loss': 0,
            'profit_loss_ratio': 0,
            'opening_date': trade.timestamp.strftime('%Y-%m-%d'),
            'timestamp': trade.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'broker_name': trade.platform,
        } for trade in saved_trades]
        
        return JsonResponse({
            'success': True,
            'trades': formatted_trades,
            'count': len(formatted_trades),
            'saved_count': saved_count,
            'mode': mode,
            'message': f'{saved_count} nouveaux trades ajoutés à la base de données'
        })
        
    except Exception as e:
        print(f"❌ Erreur AJAX Binance: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@csrf_exempt
@require_http_methods(["POST"])
def binance_positions_ajax(request):
    """Vue AJAX pour synchroniser les positions Binance"""
    try:
        from .brokers.factory import BrokerFactory
        from .models import BrokerCredentials, Position, AssetTradable, Asset, AssetType, Market
        
        # Récupérer les credentials Binance
        binance_credentials = BrokerCredentials.objects.filter(
            broker_type='binance', 
            is_active=True
        ).first()
        
        if not binance_credentials:
            return JsonResponse({'success': False, 'error': 'Aucune configuration Binance active trouvée'})
        
        credentials = binance_credentials.get_credentials_dict()
        binance_broker = BrokerFactory.create_broker('binance', request.user, credentials)
        
        # Récupérer les positions depuis Binance
        positions_data = binance_broker.get_positions()
        
        print(f"🔍 {len(positions_data)} positions récupérées depuis Binance")
        
        # Récupérer les positions existantes en base pour comparaison
        existing_positions = Position.objects.filter(
            user=request.user
        ).values_list('asset_tradable__symbol', 'side', 'size')
        
        existing_positions_set = set()
        for position in existing_positions:
            symbol, side, size = position
            position_key = (symbol, side, float(size))
            existing_positions_set.add(position_key)
        
        print(f"📊 {len(existing_positions)} positions existantes en base de données")
        
        # Sauvegarder les nouvelles positions
        saved_count = 0
        for position_data in positions_data:
            try:
                asset_symbol = position_data.get('asset', 'N/A')
                
                # Créer ou récupérer l'asset
                asset, created = Asset.objects.get_or_create(
                    symbol=asset_symbol,
                    defaults={'name': asset_symbol, 'sector': 'Cryptocurrency', 'industry': 'Digital Assets', 'market_cap': 0.0, 'price_history': 'xxxx'}
                )
                
                asset_type, _ = AssetType.objects.get_or_create(name='Crypto')
                market, _ = Market.objects.get_or_create(name='Binance')
                
                asset_tradable, created = AssetTradable.objects.get_or_create(
                    symbol=asset_symbol,
                    platform='binance',
                    defaults={'asset': asset, 'name': asset_symbol, 'asset_type': asset_type, 'market': market}
                )
                
                position_size = float(position_data.get('total', 0))
                position_side = 'BUY'  # Par défaut pour les balances
                
                position_key = (asset_symbol, position_side, position_size)
                
                if position_key not in existing_positions_set and position_size > 0:
                    position = Position.objects.create(
                        user=request.user,
                        asset_tradable=asset_tradable,
                        size=position_size,
                        entry_price=0.0,  # Pas de prix d'entrée pour les balances
                        current_price=0.0,  # À récupérer si nécessaire
                        side=position_side,
                        status='OPEN',
                        pnl=0.0
                    )
                    saved_count += 1
                    print(f"✅ Nouvelle position sauvegardée: {asset_symbol} {position_side} {position_size}")
                else:
                    print(f"⏭️ Position déjà existante: {asset_symbol} {position_side} {position_size}")
                    
            except Exception as e:
                print(f"❌ Erreur sauvegarde position {position_data.get('asset', 'N/A')}: {e}")
                continue
        
        # Récupérer toutes les positions sauvegardées pour l'affichage
        saved_positions = Position.objects.filter(user=request.user).select_related('asset_tradable__asset')
        
        formatted_positions = []
        for position in saved_positions:
            formatted_positions.append({
                'id': position.id,
                'asset_name': position.asset_tradable.name,
                'asset_symbol': position.asset_tradable.symbol,
                'underlying_asset_name': position.asset_tradable.asset.name,
                'size': str(position.size),
                'entry_price': str(position.entry_price),
                'current_price': str(position.current_price),
                'side': position.side,
                'status': position.status,
                'pnl': str(position.pnl),
                'created_at': position.created_at.isoformat(),
                'updated_at': position.updated_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'positions': formatted_positions,
            'count': len(formatted_positions),
            'saved_count': saved_count,
            'message': f'{saved_count} nouvelles positions ajoutées à la base de données'
        })
        
    except Exception as e:
        print(f"❌ Erreur AJAX positions Binance: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

