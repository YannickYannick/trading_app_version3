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
        
        from decimal import Decimal
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
            
            # Récupérer ou créer AssetType et Market
            asset_type, _ = AssetType.objects.get_or_create(name=data.get('asset_type', 'Unknown'))
            market, _ = Market.objects.get_or_create(name=data.get('market', 'Unknown'))
            
            # Créer ou mettre à jour AssetTradable
            asset_tradable, created = AssetTradable.objects.get_or_create(
                symbol=data['symbol'],
                platform=data['platform'],
                defaults={
                    'name': data.get('name', ''),
                    'asset_type': asset_type,
                    'market': market,
                }
            )
            
            if not created:
                # Mise à jour si l'objet existe déjà
                asset_tradable.name = data.get('name', '')
                asset_tradable.asset_type = asset_type
                asset_tradable.market = market
                asset_tradable.save()
            
            return JsonResponse({'status': 'success', 'message': 'AssetTradable sauvegardé'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Erreur: {str(e)}'})
    
    # Récupérer les données pour Tabulator
    asset_tradables = AssetTradable.objects.select_related('asset_type', 'market').all()
    data_asset_tradables = []
    
    for at in asset_tradables:
        data_asset_tradables.append({
            'id': at.id,
            'symbol': at.symbol,
            'name': at.name,
            'platform': at.platform,
            'asset_type': at.asset_type.name,
            'market': at.market.name,
            'created_at': at.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    
    return render(request, 'trading_app/asset_tradable_tabulator.html', {
        'data_asset_tradables': data_asset_tradables
    })

