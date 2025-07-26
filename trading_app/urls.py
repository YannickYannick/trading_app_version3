from django.urls import path
from .views import (
    asset_list, asset_tabulator, save_asset_ajax,
    trade_tabulator, position_tabulator, strategy_tabulator,
    broker_dashboard, broker_config, saxo_auth_callback, saxo_auth_url,
    sync_broker_data, place_broker_order, test_broker_connection,
    asset_tradable_tabulator, asset_search_tabulator, update_all_assets_with_yahoo, place_order_view
)

urlpatterns = [
    path('assets/', asset_list, name='asset_list'),
    path('assets/tabulator/', asset_tabulator, name='asset_tabulator'),
    path('assets/save/', save_asset_ajax, name='save_asset_ajax'),
    path('trades/tabulator/', trade_tabulator, name='trade_tabulator'),
    path('positions/tabulator/', position_tabulator, name='position_tabulator'),
    path('strategies/tabulator/', strategy_tabulator, name='strategy_tabulator'),
    
    # URLs pour les courtiers
    path('brokers/', broker_dashboard, name='broker_dashboard'),
    path('brokers/config/', broker_config, name='broker_config'),
    path('brokers/config/<int:broker_id>/', broker_config, name='broker_config_edit'),
    path('brokers/saxo/auth-url/', saxo_auth_url, name='saxo_auth_url'),
    path('brokers/saxo/callback/', saxo_auth_callback, name='saxo_auth_callback'),
    path('brokers/<int:broker_id>/test/', test_broker_connection, name='test_broker_connection'),
    path('brokers/<int:broker_id>/sync/', sync_broker_data, name='sync_broker_data'),
    path('brokers/<int:broker_id>/order/', place_broker_order, name='place_broker_order'),
    path('asset-tradable/', asset_tradable_tabulator, name='asset_tradable_tabulator'),
    path('asset-tradable/search/', asset_search_tabulator, name='asset_search_tabulator'),
    path('asset-tradable/update-all/', update_all_assets_with_yahoo, name='update_all_assets_with_yahoo'),
    path('order/place/', place_order_view, name='place_order_view'),
] 