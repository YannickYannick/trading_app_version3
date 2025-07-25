from django.urls import path
from .views import (
    asset_list, asset_tabulator, save_asset_ajax,
    trade_tabulator, position_tabulator, strategy_tabulator,
    broker_dashboard, broker_config, saxo_auth_callback,
    sync_broker_data, place_broker_order, test_broker_connection
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
    path('brokers/saxo/callback/', saxo_auth_callback, name='saxo_auth_callback'),
    path('brokers/<int:broker_id>/test/', test_broker_connection, name='test_broker_connection'),
    path('brokers/<int:broker_id>/sync/', sync_broker_data, name='sync_broker_data'),
    path('brokers/<int:broker_id>/order/', place_broker_order, name='place_broker_order'),
] 