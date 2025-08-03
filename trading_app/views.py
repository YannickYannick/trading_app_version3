from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db import transaction, models
from django.db.models import Q
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
import pandas as pd
import time
from django.core.serializers.json import DjangoJSONEncoder
from .brokers.factory import BrokerFactory
from .models import Asset, Position, Trade, Strategy, BrokerCredentials, AssetType, Market, AssetTradable, AllAssets

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



def asset_tabulator(request):
    # Récupérer tous les Asset mis à jour par Yahoo Finance
    assets = Asset.objects.all()
    
    # Dictionnaire pour regrouper par symbole
    grouped_assets = {}
    
    for asset in assets:
        symbol = asset.symbol_clean or asset.symbol
        
        if symbol not in grouped_assets:
            # Récupérer les données depuis Asset
            sector = asset.sector or 'Non défini'
            industry = asset.industry or 'Non défini'
            market_cap = float(asset.market_cap) if asset.market_cap else 0.0
            
            # Traiter l'historique des prix
            price_history_display = 'Non disponible'
            last_price = 0.0
            if asset.price_history and asset.price_history != 'xxxx':
                try:
                    price_data = json.loads(asset.price_history)
                    if price_data and len(price_data) >= 3:
                        # Prendre les 3 dernières valeurs de prix de fermeture
                        last_3_closes = [str(round(candle['close'], 2)) for candle in price_data[-3:]]
                        price_history_display = ', '.join(last_3_closes)
                        # Récupérer le dernier prix pour le calcul de la valeur
                        last_price = float(price_data[-1]['close'])
                    elif price_data:
                        # Si moins de 3 valeurs, prendre toutes
                        last_closes = [str(round(candle['close'], 2)) for candle in price_data]
                        price_history_display = ', '.join(last_closes)
                        # Récupérer le dernier prix pour le calcul de la valeur
                        last_price = float(price_data[-1]['close'])
                except (json.JSONDecodeError, KeyError, IndexError):
                    price_history_display = 'Erreur format'
            
            # Chercher s'il y a un AssetTradable correspondant
            asset_tradable = None
            try:
                asset_tradable = AssetTradable.objects.get(symbol=symbol)
            except AssetTradable.DoesNotExist:
                # Essayer de trouver par symbole nettoyé
                clean_symbol = symbol.split(':')[0] if ':' in symbol else symbol
                clean_symbol = clean_symbol.split('_')[0] if '_' in clean_symbol else clean_symbol
                try:
                    asset_tradable = AssetTradable.objects.get(symbol=clean_symbol)
                except AssetTradable.DoesNotExist:
                    pass
            
            # Calculer la taille totale depuis toutes les positions correspondantes
            total_size = 0.0
            if request.user.is_authenticated:
                # Nettoyer le symbole pour la recherche
                base_symbol = symbol.split(':')[0] if ':' in symbol else symbol
                base_symbol = base_symbol.split('_')[0] if '_' in base_symbol else base_symbol
                base_symbol = base_symbol.upper()
                
                # Chercher tous les AssetTradable qui correspondent au symbole de base
                matching_asset_tradables = AssetTradable.objects.filter(
                    symbol__startswith=base_symbol
                )
                
                # Calculer la taille totale de toutes les positions correspondantes
                for at in matching_asset_tradables:
                    positions_size = Position.objects.filter(
                        asset_tradable=at,
                        user=request.user
                    ).aggregate(
                        total_size=models.Sum('size')
                    )['total_size'] or 0
                    total_size += float(positions_size)
                
                print(f"🔍 Symbole: {symbol}, Base: {base_symbol}, AssetTradables trouvés: {matching_asset_tradables.count()}, Taille totale: {total_size}")
            
            # Calculer la valeur (size * dernier prix)
            value = total_size * last_price
            
            grouped_assets[symbol] = {
                'id': asset.id,
                'symbol': symbol,
                'name': asset.name,
                'platform': asset_tradable.platform if asset_tradable else 'Non défini',
                'asset_type': asset_tradable.asset_type.name if asset_tradable else 'Non défini',
                'market': asset_tradable.market.name if asset_tradable else 'Non défini',
                'sector': sector,
                'industry': industry,
                'market_cap': market_cap,
                'size': total_size,
                'value': value,
                'price_history': price_history_display,
                'all_asset_id': asset_tradable.all_asset.id if asset_tradable and asset_tradable.all_asset else None,
            }
    
    # Convertir le dictionnaire en liste
    data_assets = list(grouped_assets.values())
    
    # Calculer les données pour les graphiques
    sector_data = {}
    industry_data = {}
    
    for asset in data_assets:
        value = asset['value']  # Utiliser la valeur au lieu de la taille
        sector = asset['sector'] or 'Non défini'
        industry = asset['industry'] or 'Non défini'
        
        # Agréger par secteur
        if sector not in sector_data:
            sector_data[sector] = 0
        sector_data[sector] += value
        
        # Agréger par industrie
        if industry not in industry_data:
            industry_data[industry] = 0
        industry_data[industry] += value
    
    # Convertir en format pour Chart.js
    chart_sector_data = [{'label': k, 'value': v} for k, v in sector_data.items() if v > 0]
    chart_industry_data = [{'label': k, 'value': v} for k, v in industry_data.items() if v > 0]
    
    return render(request, 'trading_app/asset_tabulator.html', {
        'data_assets': json.dumps(data_assets, cls=DjangoJSONEncoder),
        'chart_sector_data': json.dumps(chart_sector_data, cls=DjangoJSONEncoder),
        'chart_industry_data': json.dumps(chart_industry_data, cls=DjangoJSONEncoder),
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
    
    # Récupérer les brokers Saxo configurés pour les boutons de synchronisation
    saxo_brokers = BrokerCredentials.objects.filter(
        user=request.user,
        broker_type='saxo',
        is_active=True
    ).order_by('name')

    return render(request, 'trading_app/trade_tabulator.html', {
        'data_trades': json.dumps(tabledata, cls=DjangoJSONEncoder),
        'saxo_brokers': saxo_brokers,
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
    positions = Position.objects.select_related('asset_tradable').all()
    data_positions = []
    
    # Calculer les données pour les graphiques
    sector_data = {}
    industry_data = {}
    
    for position in positions:
        position_data = {
            'id': position.id,
            'user_id': position.user_id,
            'asset_tradable_id': position.asset_tradable_id,
            'asset_name': position.asset_tradable.name,
            'asset_symbol': position.asset_tradable.symbol,
            'underlying_asset_name': position.asset_tradable.name,
            'underlying_asset_symbol': position.asset_tradable.symbol,
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
        
        # Agréger les données pour les graphiques
        size = float(position.size)
        # Pour l'instant, on utilise des valeurs par défaut car sector/industry ne sont plus dans Asset
        sector = 'Non défini'
        industry = 'Non défini'
        
        # Agréger par secteur
        if sector not in sector_data:
            sector_data[sector] = 0
        sector_data[sector] += size
        
        # Agréger par industrie
        if industry not in industry_data:
            industry_data[industry] = 0
        industry_data[industry] += size
    
    # Convertir en format pour Chart.js
    chart_sector_data = [{'label': k, 'value': v} for k, v in sector_data.items() if v > 0]
    chart_industry_data = [{'label': k, 'value': v} for k, v in industry_data.items() if v > 0]
    
    # Récupérer les brokers Saxo configurés pour les boutons de synchronisation
    saxo_brokers = BrokerCredentials.objects.filter(
        user=request.user,
        broker_type='saxo',
        is_active=True
    ).order_by('name')
    
    return render(request, 'trading_app/position_tabulator.html', {
        'data_positions': json.dumps(data_positions, cls=DjangoJSONEncoder),
        'saxo_brokers': saxo_brokers,
        'chart_sector_data': json.dumps(chart_sector_data, cls=DjangoJSONEncoder),
        'chart_industry_data': json.dumps(chart_industry_data, cls=DjangoJSONEncoder),
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
            result = broker_service.sync_trades_from_broker(broker_creds)
            if result['success']:
                return JsonResponse({
                    "success": True,
                    "message": f"{result['saved_count']} nouveaux trades synchronisés sur {result['total_trades']} au total"
                })
            else:
                return JsonResponse({
                    "success": False,
                    "error": result['error']
                }, status=400)
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
            
            # Trouver un AllAssets correspondant existant
            all_asset = AssetTradable.find_matching_all_asset(symbol, data.get('platform', 'saxo'))
            
            if not all_asset:
                return JsonResponse({'status': 'error', 'message': f'Aucun AllAssets trouvé pour le symbole {symbol}. Veuillez d\'abord ajouter cet actif dans le catalogue AllAssets.'})
            
            # Récupérer ou créer l'AssetTradable
            asset_tradable, created_tradable = AssetTradable.objects.get_or_create(
                symbol=symbol.upper(),
                platform=data.get('platform', 'saxo'),
                defaults={
                    'all_asset': all_asset,
                    'name': asset_data['name'],
                    'asset_type': asset_type,
                    'market': market,
                }
            )
            
            if not created_tradable:
                # Mise à jour si l'objet existe déjà
                asset_tradable.name = asset_data['name']
                asset_tradable.asset_type = asset_type
                asset_tradable.market = market
                asset_tradable.save()
            
            return JsonResponse({'status': 'success', 'message': 'AssetTradable sauvegardé'})
            
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde: {e}")
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
            'sector': 'Non défini',  # Plus disponible depuis Asset
            'industry': 'Non défini',  # Plus disponible depuis Asset
            'market_cap': 0.0,  # Plus disponible depuis Asset
            'created_at': at.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    
    return render(request, 'trading_app/asset_tradable_tabulator.html', {
        'data_asset_tradables': json.dumps(data_asset_tradables, cls=DjangoJSONEncoder)
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
                            'sector': 'Non défini',  # Plus disponible depuis Asset
                            'industry': 'Non défini',  # Plus disponible depuis Asset
                            'market_cap': 0.0,  # Plus disponible depuis Asset
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
                            'sector': 'Non défini',  # Plus disponible depuis Asset
                            'industry': 'Non défini',  # Plus disponible depuis Asset
                            'market_cap': 0.0,  # Plus disponible depuis Asset
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
            'sector': 'Non défini',  # Plus disponible depuis Asset
            'industry': 'Non défini',  # Plus disponible depuis Asset
            'market_cap': 0.0,  # Plus disponible depuis Asset
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
        
        # Essayer différents symboles pour les cryptomonnaies
        symbols_to_try = [clean_symbol]
        
        # Pour les cryptomonnaies, essayer avec -USD
        if clean_symbol in ["BTC", "ETH", "SOL", "AVAX", "BNB", "ADA", "DOT", "LINK", "UNI", "MATIC"]:
            symbols_to_try.append(f"{clean_symbol}-USD")
        
        # Pour les paires EUR, essayer sans EUR
        if clean_symbol.endswith("EUR"):
            base_symbol = clean_symbol[:-3]  # Enlever EUR
            symbols_to_try.extend([base_symbol, f"{base_symbol}-USD"])
        
        # Essayer chaque symbole jusqu'à ce qu'un fonctionne
        ticker = None
        working_symbol = None
        
        for try_symbol in symbols_to_try:
            try:
                print(f"🔍 Essai avec le symbole: {try_symbol}")
                ticker = yf.Ticker(try_symbol)
                # Tester si le ticker a des données
                hist = ticker.history(period="1d")
                if not hist.empty:
                    working_symbol = try_symbol
                    print(f"✅ Symbole fonctionnel trouvé: {working_symbol}")
                    break
            except Exception as e:
                print(f"❌ Échec avec {try_symbol}: {e}")
                continue
        
        if not ticker or working_symbol is None:
            print(f"❌ Aucun symbole fonctionnel trouvé pour {symbol}")
            return None
        
        # Prix actuel
        hist = ticker.history(period="1d")
        current_price = hist["Close"].iloc[-1] if not hist.empty else 0.0
        print(f"💰 Prix actuel: {current_price}")
        
        # Historique des prix sur 5 ans (format hebdomadaire)
        hist_5y = ticker.history(period="5y", interval="1wk")
        price_history_data = []
        
        if not hist_5y.empty:
            for index, row in hist_5y.iterrows():
                candle_data = {
                    'date': index.strftime('%Y-%m-%d'),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']) if not pd.isna(row['Volume']) else 0
                }
                price_history_data.append(candle_data)
            
            print(f"📊 Historique récupéré: {len(price_history_data)} bougies sur 5 ans")
        else:
            print(f"⚠️ Pas d'historique disponible pour {symbol}")
        
        # Métadonnées
        info = ticker.info
        print(f"📋 Info disponibles: {list(info.keys())}")
        
        # Gérer les cas où les données sont manquantes
        market_cap = info.get("marketCap", 0.0)
        if market_cap == "N/A" or market_cap is None:
            market_cap = 0.0
            
        # Détecter si c'est une cryptomonnaie
        quote_type = info.get("quoteType", "")
        is_crypto = quote_type == "CRYPTOCURRENCY" or symbol.endswith("USDT") or symbol.endswith("BTC") or symbol.endswith("ETH") or symbol.endswith("EUR")
        
        # Détection spéciale pour les cryptomonnaies connues
        crypto_symbols = ["BTC", "ETH", "SOL", "AVAX", "BNB", "ADA", "DOT", "LINK", "UNI", "MATIC"]
        if any(crypto in symbol.upper() for crypto in crypto_symbols):
            is_crypto = True
        
        if is_crypto:
            sector = "Crypto"
            industry = "Crypto"
            print(f"🔐 Détecté comme cryptomonnaie: {symbol}")
        else:
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
        print(f"   - Historique: {len(price_history_data)} bougies")
        
        return {
            'symbol': symbol,
            'name': name,
            'type': 'Stock',
            'market': 'Yahoo',
            'sector': sector,
            'industry': industry,
            'market_cap': market_cap,
            'price_history': json.dumps(price_history_data),
            'current_price': current_price,
        }
        
    except Exception as e:
        print(f"❌ Erreur Yahoo Finance pour {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_crypto_data(symbol: str) -> dict:
    """Récupère les données d'une cryptomonnaie depuis CoinGecko API"""
    try:
        print(f"🪙 Recherche CoinGecko pour: {symbol}")
        
        # Mapping des symboles vers les IDs CoinGecko
        crypto_mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum', 
            'ETHW': 'ethereum',  # Utiliser Ethereum standard pour ETHW
            'SOL': 'solana',
            'AVAX': 'avalanche-2',
            'BNB': 'binancecoin',
            'ADA': 'cardano',
            'DOT': 'polkadot',
            'LINK': 'chainlink',
            'UNI': 'uniswap',
            'MATIC': 'matic-network',
            'USDT': 'tether',
            'USDC': 'usd-coin',
            'DAI': 'dai',
            'LTC': 'litecoin',
            'XRP': 'ripple',
            'DOGE': 'dogecoin',
            'SHIB': 'shiba-inu',
            'TRX': 'tron',
            'BCH': 'bitcoin-cash',
            'XLM': 'stellar'
        }
        
        # Nettoyer le symbole
        clean_symbol = symbol.split(':')[0] if ':' in symbol else symbol
        clean_symbol = clean_symbol.split('_')[0] if '_' in clean_symbol else clean_symbol
        clean_symbol = clean_symbol.upper()
        
        # Chercher l'ID CoinGecko
        coin_id = None
        
        # Gérer les paires de devises (ex: ETHEUR -> ETH, BTCEUR -> BTC)
        if clean_symbol.endswith('EUR'):
            base_symbol = clean_symbol[:-3]  # Enlever EUR
            if base_symbol in crypto_mapping:
                coin_id = crypto_mapping[base_symbol]
                print(f"🔄 Paire EUR détectée: {clean_symbol} -> {base_symbol}")
        
        # Si pas trouvé, chercher dans le mapping normal
        if not coin_id:
            for sym, cg_id in crypto_mapping.items():
                if clean_symbol == sym or clean_symbol.endswith(sym):
                    coin_id = cg_id
                    break
        
        if not coin_id:
            print(f"❌ Symbole crypto non reconnu: {clean_symbol}")
            return None
        
        print(f"🔍 ID CoinGecko trouvé: {coin_id}")
        
        # Récupérer les données de base avec retry
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        
        # Retry jusqu'à 3 fois en cas d'erreur 429
        for attempt in range(3):
            response = requests.get(url)
            
            if response.status_code == 200:
                break
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 2  # Attendre 2s, puis 4s, puis 6s
                print(f"⚠️ Limite API atteinte, attente de {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"❌ Erreur API CoinGecko: {response.status_code}")
                return None
        else:
            print(f"❌ Échec après 3 tentatives pour {coin_id}")
            return None
        
        data = response.json()
        
        # Prix actuel
        current_price = data['market_data']['current_price']['usd']
        
        # Market cap
        market_cap = data['market_data']['market_cap']['usd']
        
        # Nom
        name = data['name']
        
        # Historique des prix (7 jours avec données quotidiennes)
        url_history = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=7&interval=daily"
        
        # Retry pour l'historique aussi
        for attempt in range(3):
            response_history = requests.get(url_history)
            
            if response_history.status_code == 200:
                break
            elif response_history.status_code == 429:
                wait_time = (attempt + 1) * 2
                print(f"⚠️ Limite API atteinte pour l'historique, attente de {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"❌ Erreur API CoinGecko pour l'historique: {response_history.status_code}")
                break
        else:
            print(f"❌ Échec après 3 tentatives pour l'historique de {coin_id}")
        
        price_history_data = []
        if response_history.status_code == 200:
            history_data = response_history.json()
            prices = history_data['prices']
            
            for timestamp_ms, price in prices:
                date = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d')
                candle_data = {
                    'date': date,
                    'open': price,
                    'high': price,  # CoinGecko ne donne pas OHLC, on utilise le prix
                    'low': price,
                    'close': price,
                    'volume': 0  # Pas de volume dans cette API
                }
                price_history_data.append(candle_data)
            
            print(f"📊 Historique récupéré: {len(price_history_data)} jours")
        
        # Respecter les limites de l'API (pas plus de 30 appels/minute pour être sûr)
        time.sleep(2.0)
        
        print(f"✅ Données CoinGecko récupérées:")
        print(f"   - Nom: {name}")
        print(f"   - Prix: {current_price}")
        print(f"   - Market Cap: {market_cap}")
        print(f"   - Historique: {len(price_history_data)} jours")
        
        return {
            'symbol': symbol,
            'name': name,
            'type': 'Crypto',
            'market': 'CoinGecko',
            'sector': 'Crypto',
            'industry': 'Crypto',
            'market_cap': market_cap,
            'price_history': json.dumps(price_history_data),
            'current_price': current_price,
        }
        
    except Exception as e:
        print(f"❌ Erreur CoinGecko pour {symbol}: {e}")
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
        
        # Trouver un AllAssets correspondant existant
        all_asset = AssetTradable.find_matching_all_asset(data['symbol'], platform)
        
        if not all_asset:
            raise Exception(f'Aucun AllAssets trouvé pour le symbole {data["symbol"]}. Veuillez d\'abord ajouter cet actif dans le catalogue AllAssets.')
        
        # Récupérer ou créer l'AssetTradable
        asset_tradable, created_tradable = AssetTradable.objects.get_or_create(
            symbol=data['symbol'].upper(),
            platform=platform,
            defaults={
                'all_asset': all_asset,
                'name': data.get('name', data['symbol']),
                'asset_type': asset_type,
                'market': market,
            }
        )
        
        # Si l'AssetTradable existe déjà, mettre à jour
        if not created_tradable:
            print(f"🔄 Mise à jour de l'AssetTradable existant: {asset_tradable.symbol}")
            asset_tradable.name = data.get('name', asset_tradable.name)
            asset_tradable.asset_type = asset_type
            asset_tradable.market = market
            asset_tradable.save()
        
        print(f"✅ AssetTradable créé/mis à jour: {asset_tradable.symbol} sur {platform}")
        return asset, asset_tradable
        
    except Exception as e:
        print(f"❌ Erreur création AssetTradable: {e}")
        raise

def asset_autocomplete(request):
    """Autocomplétion pour les Assets"""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})
    
    # Chercher dans AllAssets d'abord
    all_assets = AllAssets.objects.filter(
        models.Q(symbol__icontains=query) | 
        models.Q(name__icontains=query)
    )[:10]
    
    results = []
    for asset in all_assets:
        clean_symbol = asset.get_clean_symbol()
        results.append({
            'id': asset.id,
            'text': f"{clean_symbol} - {asset.name}",
            'symbol': clean_symbol,
            'name': asset.name,
            'platform': asset.platform,
            'asset_type': asset.asset_type,
            'market': asset.market,
            'source': 'all_assets'
        })
    
    # Si pas assez de résultats, ajouter des suggestions basées sur le query
    if len(results) < 5:
        # Suggestions pour les cryptomonnaies populaires
        crypto_suggestions = ['BTC', 'ETH', 'SOL', 'AVAX', 'BNB', 'ADA', 'DOT', 'LINK', 'UNI', 'MATIC']
        for crypto in crypto_suggestions:
            if query.upper() in crypto and not any(r['symbol'] == crypto for r in results):
                results.append({
                    'id': f'crypto_{crypto}',
                    'text': f"{crypto} - {crypto} (Cryptomonnaie)",
                    'symbol': crypto,
                    'name': f"{crypto} (Cryptomonnaie)",
                    'platform': 'binance',
                    'asset_type': 'Crypto',
                    'market': 'SPOT',
                    'source': 'suggestion'
                })
        
        # Suggestions pour les actions populaires
        stock_suggestions = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NVDA', 'NFLX']
        for stock in stock_suggestions:
            if query.upper() in stock and not any(r['symbol'] == stock for r in results):
                results.append({
                    'id': f'stock_{stock}',
                    'text': f"{stock} - {stock} (Action)",
                    'symbol': stock,
                    'name': f"{stock} (Action)",
                    'platform': 'yahoo',
                    'asset_type': 'Stock',
                    'market': 'NASDAQ',
                    'source': 'suggestion'
                })
    
    return JsonResponse({'results': results[:10]})

def create_asset(request):
    """Crée un nouvel Asset avec synchronisation automatique"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            symbol = data.get('symbol', '').strip().upper()
            name = data.get('name', '').strip()
            source = data.get('source', 'manual')  # 'all_assets', 'suggestion', 'manual'
            
            if not symbol:
                return JsonResponse({'success': False, 'error': 'Symbole requis'})
            
            # Vérifier si l'Asset existe déjà
            existing_asset = Asset.objects.filter(symbol_clean=symbol).first()
            if existing_asset:
                return JsonResponse({'success': False, 'error': f'Asset {symbol} existe déjà'})
            
            # Créer le nouvel Asset
            asset = Asset.objects.create(
                symbol=symbol,  # Symbole original
                symbol_clean=symbol,  # Symbole nettoyé (même chose ici)
                name=name or symbol,
                sector='xxxx',
                industry='xxxx',
                market_cap=0.0,
                price_history='xxxx'
            )
            
            # Si c'est un AllAssets existant, créer la référence
            if source == 'all_assets' and data.get('all_asset_id'):
                try:
                    all_asset = AllAssets.objects.get(id=data['all_asset_id'])
                    asset.all_asset = all_asset
                    asset.save()
                except AllAssets.DoesNotExist:
                    pass
            
            # Synchronisation automatique avec Yahoo/CoinGecko
            print(f"🔄 Synchronisation automatique pour {symbol}")
            
            # Détecter si c'est une cryptomonnaie
            crypto_symbols = ["BTC", "ETH", "ETHW", "SOL", "AVAX", "BNB", "ADA", "DOT", "LINK", "UNI", "MATIC", "USDT", "USDC", "DAI", "LTC", "XRP", "DOGE", "SHIB", "TRX", "BCH", "XLM"]
            is_crypto = any(crypto in symbol.upper() for crypto in crypto_symbols)
            
            if is_crypto:
                print(f"🪙 Synchronisation CoinGecko pour {symbol}")
                crypto_data = get_crypto_data(symbol)
                if crypto_data:
                    asset.name = crypto_data.get('name', asset.name)
                    asset.sector = crypto_data.get('sector', asset.sector)
                    asset.industry = crypto_data.get('industry', asset.industry)
                    asset.market_cap = crypto_data.get('market_cap', asset.market_cap)
                    asset.price_history = crypto_data.get('price_history', asset.price_history)
                    asset.save()
                    print(f"✅ {symbol} synchronisé avec CoinGecko")
                else:
                    print(f"⚠️ Pas de données CoinGecko pour {symbol}")
            else:
                print(f"📈 Synchronisation Yahoo pour {symbol}")
                yahoo_data = get_yahoo_data(symbol)
                if yahoo_data:
                    asset.name = yahoo_data.get('name', asset.name)
                    asset.sector = yahoo_data.get('sector', asset.sector)
                    asset.industry = yahoo_data.get('industry', asset.industry)
                    asset.market_cap = yahoo_data.get('market_cap', asset.market_cap)
                    asset.price_history = yahoo_data.get('price_history', asset.price_history)
                    asset.save()
                    print(f"✅ {symbol} synchronisé avec Yahoo")
                else:
                    print(f"⚠️ Pas de données Yahoo pour {symbol}")
            
            return JsonResponse({
                'success': True, 
                'message': f'Asset {symbol} créé avec succès',
                'asset_id': asset.id
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Données JSON invalides'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

def get_asset_price_history(request, asset_id):
    """Récupère l'historique des prix d'un Asset"""
    print(f"🔍 Requête historique pour asset ID: {asset_id}")
    
    try:
        asset = Asset.objects.get(id=asset_id)
        print(f"✅ Asset trouvé: {asset.symbol} - {asset.name}")
        print(f"📊 Historique: {asset.price_history[:100]}..." if asset.price_history else "Aucun historique")
        
        if not asset.price_history or asset.price_history == 'xxxx':
            print(f"⚠️ Pas d'historique pour {asset.symbol}")
            return JsonResponse({
                'success': False, 
                'error': 'Aucun historique disponible pour cet asset'
            })
        
        # Parser l'historique JSON
        try:
            price_data = json.loads(asset.price_history)
            print(f"📊 Données parsées: {len(price_data)} bougies")
            if price_data:
                print(f"📊 Première bougie: {price_data[0]}")
        except json.JSONDecodeError as e:
            print(f"❌ Erreur JSON: {e}")
            return JsonResponse({
                'success': False, 
                'error': 'Format d\'historique invalide'
            })
        
        # Convertir au format TradingView
        chart_data = []
        for candle in price_data:
            # TradingView attend : {time: timestamp, open: float, high: float, low: float, close: float}
            # Nos données ont : {"date": "2023-01-01", "open": 100, ...}
            try:
                # Convertir la date en timestamp
                date_obj = datetime.strptime(candle['date'], '%Y-%m-%d')
                timestamp = int(date_obj.timestamp())
                
                chart_data.append({
                    'time': timestamp,
                    'open': float(candle['open']),
                    'high': float(candle['high']),
                    'low': float(candle['low']),
                    'close': float(candle['close']),
                    'volume': float(candle.get('volume', 0))
                })
            except (KeyError, ValueError) as e:
                print(f"⚠️ Erreur parsing candle: {e}")
                continue
        
        # Trier par date
        chart_data.sort(key=lambda x: x['time'])
        
        return JsonResponse({
            'success': True,
            'data': {
                'symbol': asset.symbol_clean or asset.symbol,
                'name': asset.name,
                'candles': chart_data,
                'period': '5Y' if len(chart_data) > 200 else '1Y' if len(chart_data) > 50 else '1M'
            }
        })
        
    except Asset.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Asset non trouvé'
        })
    except Exception as e:
        print(f"❌ Erreur dans get_asset_price_history: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': f'Erreur: {str(e)}'
        })

def update_all_assets_with_yahoo(request):
    """Met à jour tous les Assets existants avec les données Yahoo Finance"""
    if request.method == 'POST':
        try:
            assets = Asset.objects.all()
            updated_count = 0
            
            for asset in assets:
                try:
                    print(f"📈 Mise à jour de {asset.symbol}...")
                    
                    # Nettoyer le symbole pour Yahoo Finance (enlever les extensions)
                    # Utiliser le symbole nettoyé
                    clean_symbol = asset.symbol_clean or asset.get_clean_symbol()
                    clean_symbol = clean_symbol.strip()
                    
                    print(f"🔍 Symbole nettoyé pour Yahoo: {clean_symbol}")
                    
                    # Détecter si c'est une cryptomonnaie
                    crypto_symbols = ["BTC", "ETH", "ETHW", "SOL", "AVAX", "BNB", "ADA", "DOT", "LINK", "UNI", "MATIC", "USDT", "USDC", "DAI", "LTC", "XRP", "DOGE", "SHIB", "TRX", "BCH", "XLM"]
                    
                    # Vérifier si c'est une crypto directe ou une paire EUR
                    is_crypto = any(crypto in clean_symbol.upper() for crypto in crypto_symbols)
                    
                    # Ajouter la détection des paires EUR
                    if clean_symbol.endswith('EUR'):
                        base_symbol = clean_symbol[:-3]
                        if base_symbol in crypto_symbols:
                            is_crypto = True
                            print(f"🔄 Paire EUR crypto détectée: {clean_symbol} -> {base_symbol}")
                    
                    if is_crypto:
                        print(f"🪙 Détecté comme cryptomonnaie, utilisation de CoinGecko")
                        crypto_data = get_crypto_data(clean_symbol)
                        
                        if crypto_data:
                            # Mettre à jour l'Asset avec les données CoinGecko
                            asset.name = crypto_data.get('name', asset.name)
                            asset.sector = crypto_data.get('sector', asset.sector)
                            asset.industry = crypto_data.get('industry', asset.industry)
                            asset.market_cap = crypto_data.get('market_cap', asset.market_cap)
                            asset.price_history = crypto_data.get('price_history', asset.price_history)
                            asset.save()
                            
                            updated_count += 1
                            print(f"✅ {asset.symbol} mis à jour (CoinGecko): {asset.sector} - {asset.industry} - {asset.market_cap} - Historique: {len(json.loads(asset.price_history)) if asset.price_history != 'xxxx' else 0} jours")
                        else:
                            print(f"⚠️ Pas de données CoinGecko pour {asset.symbol} (symbole nettoyé: {clean_symbol})")
                    else:
                        # Utiliser Yahoo Finance pour les actions/autres
                        yahoo_data = get_yahoo_data(clean_symbol)
                        
                        if yahoo_data:
                            # Mettre à jour l'Asset avec les données Yahoo
                            asset.name = yahoo_data.get('name', asset.name)
                            asset.sector = yahoo_data.get('sector', asset.sector)
                            asset.industry = yahoo_data.get('industry', asset.industry)
                            asset.market_cap = yahoo_data.get('market_cap', asset.market_cap)
                            asset.price_history = yahoo_data.get('price_history', asset.price_history)
                            asset.save()
                            
                            updated_count += 1
                            print(f"✅ {asset.symbol} mis à jour (Yahoo): {asset.sector} - {asset.industry} - {asset.market_cap} - Historique: {len(json.loads(asset.price_history)) if asset.price_history != 'xxxx' else 0} bougies")
                        else:
                            print(f"⚠️ Pas de données Yahoo pour {asset.symbol} (symbole nettoyé: {clean_symbol})")
                        
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
    asset_tradables = AssetTradable.objects.select_related('asset_type', 'market').all()
    
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
                
                # Trouver un AllAssets correspondant existant
                all_asset = AssetTradable.find_matching_all_asset(symbol, 'binance')
                
                if not all_asset:
                    print(f"⚠️ Aucun AllAssets trouvé pour {symbol}, trade ignoré")
                    continue
                
                # Créer ou récupérer AssetTradable
                asset_tradable, created = AssetTradable.objects.get_or_create(
                    symbol=symbol.upper(),
                    platform='binance',
                    defaults={
                        'all_asset': all_asset,
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

@login_required
@csrf_exempt
def sync_saxo_trades(request, broker_id):
    """Synchroniser les trades depuis un broker Saxo spécifique"""
    try:
        # Récupérer le broker
        broker_creds = get_object_or_404(BrokerCredentials, id=broker_id, user=request.user, broker_type='saxo')
        
        # Créer le service broker
        broker_service = BrokerService(request.user)
        
        # Synchroniser les trades
        result = broker_service.sync_trades_from_broker(broker_creds)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': f"✅ {result.get('saved_count', 0)} nouveaux trades Saxo synchronisés",
                'saved_count': result.get('saved_count', 0),
                'total_trades': result.get('total_trades', 0)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Erreur inconnue lors de la synchronisation')
            }, status=400)
            
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation des trades Saxo: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f"Erreur lors de la synchronisation: {str(e)}"
        }, status=500)

@login_required
@csrf_exempt
def sync_saxo_positions(request, broker_id):
    """Synchroniser les positions depuis un broker Saxo spécifique"""
    try:
        # Récupérer le broker
        broker_creds = get_object_or_404(BrokerCredentials, id=broker_id, user=request.user, broker_type='saxo')
        
        # Créer le service broker
        broker_service = BrokerService(request.user)
        
        # Synchroniser les positions
        positions = broker_service.sync_positions_from_broker(broker_creds)
        
        # Compter le nombre total de positions pour ce broker
        total_positions = Position.objects.filter(
            user=broker_creds.user,
            asset_tradable__platform=broker_creds.broker_type
        ).count()
        
        return JsonResponse({
            'success': True,
            'message': f"✅ {len(positions)} positions Saxo synchronisées",
            'saved_count': len(positions),
            'total_positions': total_positions
        })
            
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation des positions Saxo: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f"Erreur lors de la synchronisation: {str(e)}"
        }, status=500)

@login_required
@csrf_exempt
def delete_all_trades(request):
    """Supprimer tous les trades de tous les brokers"""
    try:
        # Compter les trades avant suppression
        trades_count = Trade.objects.filter(user=request.user).count()
        
        # Supprimer tous les trades de l'utilisateur
        Trade.objects.filter(user=request.user).delete()
        
        return JsonResponse({
            'success': True,
            'message': f"✅ {trades_count} trades supprimés avec succès",
            'deleted_count': trades_count
        })
            
    except Exception as e:
        logger.error(f"Erreur lors de la suppression des trades: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f"Erreur lors de la suppression: {str(e)}"
        }, status=500)

@login_required
@csrf_exempt
def update_all_trades(request):
    """Mettre à jour tous les trades de tous les brokers"""
    try:
        # Récupérer tous les brokers configurés
        brokers = BrokerCredentials.objects.filter(user=request.user, is_active=True)
        broker_service = BrokerService(request.user)
        
        total_updated = 0
        results = []
        
        for broker in brokers:
            try:
                # Synchroniser les trades pour ce broker
                result = broker_service.sync_trades_from_broker(broker)
                if result['success']:
                    total_updated += result.get('saved_count', 0)
                    results.append(f"{broker.name}: {result.get('saved_count', 0)} trades")
                else:
                    results.append(f"{broker.name}: Erreur - {result.get('error', 'Erreur inconnue')}")
            except Exception as e:
                results.append(f"{broker.name}: Erreur - {str(e)}")
        
        return JsonResponse({
            'success': True,
            'message': f"✅ {total_updated} trades mis à jour au total",
            'updated_count': total_updated,
            'details': results
        })
            
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des trades: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f"Erreur lors de la mise à jour: {str(e)}"
        }, status=500)

@login_required
@csrf_exempt
def delete_all_positions(request):
    """Supprimer toutes les positions de tous les brokers"""
    try:
        # Compter les positions avant suppression
        positions_count = Position.objects.filter(user=request.user).count()
        
        # Supprimer toutes les positions de l'utilisateur
        Position.objects.filter(user=request.user).delete()
        
        return JsonResponse({
            'success': True,
            'message': f"✅ {positions_count} positions supprimées avec succès",
            'deleted_count': positions_count
        })
            
    except Exception as e:
        logger.error(f"Erreur lors de la suppression des positions: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f"Erreur lors de la suppression: {str(e)}"
        }, status=500)

@login_required
@csrf_exempt
def update_all_positions(request):
    """Mettre à jour toutes les positions de tous les brokers"""
    try:
        # Récupérer tous les brokers configurés
        brokers = BrokerCredentials.objects.filter(user=request.user, is_active=True)
        broker_service = BrokerService(request.user)
        
        total_updated = 0
        results = []
        
        for broker in brokers:
            try:
                # Synchroniser les positions pour ce broker
                positions = broker_service.sync_positions_from_broker(broker)
                total_updated += len(positions)
                results.append(f"{broker.name}: {len(positions)} positions")
            except Exception as e:
                results.append(f"{broker.name}: Erreur - {str(e)}")
        
        return JsonResponse({
            'success': True,
            'message': f"✅ {total_updated} positions mises à jour au total",
            'updated_count': total_updated,
            'details': results
        })
            
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des positions: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f"Erreur lors de la mise à jour: {str(e)}"
        }, status=500)

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
                
                # Trouver un AllAssets correspondant existant
                all_asset = AssetTradable.find_matching_all_asset(asset_symbol, 'binance')
                
                if not all_asset:
                    print(f"⚠️ Aucun AllAssets trouvé pour {asset_symbol}, position ignorée")
                    continue
                
                asset_tradable, created = AssetTradable.objects.get_or_create(
                    symbol=asset_symbol.upper(),
                    platform='binance',
                    defaults={'all_asset': all_asset, 'name': asset_symbol, 'asset_type': asset_type, 'market': market}
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
        saved_positions = Position.objects.filter(user=request.user).select_related('asset_tradable')
        
        formatted_positions = []
        for position in saved_positions:
            formatted_positions.append({
                'id': position.id,
                'asset_name': position.asset_tradable.name,
                'asset_symbol': position.asset_tradable.symbol,
                'underlying_asset_name': position.asset_tradable.name,
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




@login_required
@csrf_exempt
def sync_all_assets(request):
    """Synchronise tous les actifs depuis tous les brokers configurés"""
    try:
        broker_service = BrokerService(request.user)
        result = broker_service.sync_all_assets_from_all_brokers()
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': result['message'],
                'total_saved': result['total_saved'],
                'total_updated': result['total_updated'],
                'broker_results': result['broker_results']
            })
        else:
            return JsonResponse({'success': False, 'error': result.get('error', 'Erreur inconnue')}, status=400)
            
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation des actifs: {str(e)}")
        return JsonResponse({'success': False, 'error': f"Erreur lors de la synchronisation: {str(e)}"}, status=500)


@login_required
@csrf_exempt
def sync_broker_assets(request, broker_id):
    """Synchronise les actifs depuis un broker spécifique"""
    try:
        broker_creds = get_object_or_404(BrokerCredentials, id=broker_id, user=request.user, is_active=True)
        broker_service = BrokerService(request.user)
        
        if broker_creds.broker_type == 'saxo':
            result = broker_service.sync_all_assets_from_saxo(broker_creds)
        elif broker_creds.broker_type == 'binance':
            result = broker_service.sync_all_assets_from_binance(broker_creds)
        else:
            return JsonResponse({'success': False, 'error': f'Broker {broker_creds.broker_type} non supporté'}, status=400)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': result['message'],
                'saved_count': result['saved_count'],
                'updated_count': result['updated_count'],
                'total_processed': result['total_processed']
            })
        else:
            return JsonResponse({'success': False, 'error': result.get('error', 'Erreur inconnue')}, status=400)
            
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation des actifs du broker {broker_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': f"Erreur lors de la synchronisation: {str(e)}"}, status=500)


@login_required
def search_all_assets(request):
    """Recherche d'actifs pour l'autocomplétion"""
    try:
        query = request.GET.get('q', '').strip()
        platform = request.GET.get('platform', '').strip()
        
        print(f"🔍 Recherche: query='{query}', platform='{platform}'")
        
        if not query or len(query) < 2:
            print("❌ Query trop courte ou vide")
            return JsonResponse({'results': []})
        
        # Construire la requête
        queryset = AllAssets.objects.filter(is_tradable=True)
        print(f"📊 Actifs tradables de base: {queryset.count()}")
        
        # Filtrer par plateforme si spécifiée
        if platform:
            queryset = queryset.filter(platform=platform)
            print(f"📊 Après filtre plateforme '{platform}': {queryset.count()}")
        
        # Recherche dans le symbole et le nom
        queryset = queryset.filter(
            Q(symbol__icontains=query) | 
            Q(name__icontains=query)
        )
        print(f"📊 Après recherche '{query}': {queryset.count()}")
        
        # Limiter les résultats
        results = queryset[:20].values('symbol', 'name', 'platform', 'asset_type', 'market')
        
        # Formater les résultats pour l'autocomplétion
        formatted_results = []
        for asset in results:
            formatted_results.append({
                'id': asset['symbol'],
                'text': f"{asset['symbol']} - {asset['name']} ({asset['platform'].upper()})",
                'symbol': asset['symbol'],
                'name': asset['name'],
                'platform': asset['platform'],
                'asset_type': asset['asset_type'],
                'market': asset['market']
            })
        
        print(f"✅ Retourne {len(formatted_results)} résultats")
        return JsonResponse({'results': formatted_results})
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        logger.error(f"Erreur lors de la recherche d'actifs: {str(e)}")
        return JsonResponse({'results': [], 'error': str(e)})


def kenza(request):
    """Page spéciale pour Kenza"""
    return render(request, 'trading_app/kenza.html')

