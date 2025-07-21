from django.urls import path
from .views import (
    asset_list, asset_tabulator, save_asset_ajax,
    trade_tabulator, position_tabulator, strategy_tabulator, save_trade_ajax
)

urlpatterns = [
    path('assets/', asset_list, name='asset_list'),
    path('assets/tabulator/', asset_tabulator, name='asset_tabulator'),
    path('assets/save/', save_asset_ajax, name='save_asset_ajax'),
    path('trades/tabulator/', trade_tabulator, name='trade_tabulator'),
    path('trades/save/', save_trade_ajax, name='save_trade_ajax'),
    path('positions/tabulator/', position_tabulator, name='position_tabulator'),
    path('strategies/tabulator/', strategy_tabulator, name='strategy_tabulator'),
] 