from django.shortcuts import render
from .models import Asset
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Trade, Position, Strategy

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

@csrf_exempt
def save_trade_ajax(request):
    if request.method == "POST":
        data = request.POST.dict() if request.POST else json.loads(request.body)
        # Vérifie les champs obligatoires
        required_fields = ["user", "asset", "size", "price", "side", "platform"]
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            return JsonResponse({"error": f"Champs manquants : {', '.join(missing)}"}, status=400)
        try:
            trade_id = data.get("id")
            if trade_id:
                trade = Trade.objects.get(id=trade_id)
            else:
                trade = Trade()
            # Remplis les champs
            trade.user_id = data["user"]  # doit être l'ID d'un User existant
            trade.asset_id = data["asset"]  # doit être l'ID d'un Asset existant
            trade.size = data["size"]
            trade.price = data["price"]
            trade.side = data["side"]
            trade.platform = data["platform"]
            # ... autres champs
            trade.save()
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)

