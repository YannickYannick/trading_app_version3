from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('brokers/', views.broker_dashboard, name='broker_dashboard'),
    path('brokers/config/', views.broker_config, name='broker_config'),
    path('brokers/config/<int:broker_id>/', views.broker_config, name='broker_config_edit'),
    path('brokers/saxo/auth-url/', views.saxo_auth_url, name='saxo_auth_url'),
    path('brokers/saxo/callback/', views.saxo_auth_callback, name='saxo_auth_callback'),
    path('brokers/<int:broker_id>/test/', views.test_broker_connection, name='test_broker_connection'),
    path('brokers/<int:broker_id>/sync/', views.sync_broker_data, name='sync_broker_data'),
    path('brokers/<int:broker_id>/sync-trades/', views.sync_saxo_trades, name='sync_saxo_trades'),
    path('brokers/<int:broker_id>/sync-positions/', views.sync_saxo_positions, name='sync_saxo_positions'),
    path('brokers/<int:broker_id>/order/', views.place_broker_order, name='place_broker_order'),
    
    path('trades/tabulator/', views.trade_tabulator, name='trade_tabulator'),
    path('trades/binance/', views.binance_trades_ajax, name='binance_trades_ajax'),
    path('trades/delete-all/', views.delete_all_trades, name='delete_all_trades'),
    path('trades/update-all/', views.update_all_trades, name='update_all_trades'),
    
    path('positions/tabulator/', views.position_tabulator, name='position_tabulator'),
    path('positions/binance/', views.binance_positions_ajax, name='binance_positions_ajax'),
    path('positions/delete-all/', views.delete_all_positions, name='delete_all_positions'),
    path('positions/update-all/', views.update_all_positions, name='update_all_positions'),
    path('database-schema/', views.database_schema, name='database_schema'),
    path('database-schema-manual/', views.database_schema_manual, name='database_schema_manual'),
    path('assets/sync-all/', views.sync_all_assets, name='sync_all_assets'),
    path('brokers/<int:broker_id>/sync-assets/', views.sync_broker_assets, name='sync_broker_assets'),
    path('assets/search/', views.search_all_assets, name='search_all_assets'),
    
    path('assets/', views.asset_list, name='asset_list'),
    path('assets/tabulator/', views.asset_tabulator, name='asset_tabulator'),
    path('assets/save/', views.save_asset_ajax, name='save_asset_ajax'),
    path('assets/tradable/tabulator/', views.asset_tradable_tabulator, name='asset_tradable_tabulator'),
    path('assets/search/tabulator/', views.asset_search_tabulator, name='asset_search_tabulator'),
    path('assets/update-yahoo/', views.update_all_assets_with_yahoo, name='update_all_assets_with_yahoo'),
    
    path('strategies/tabulator/', views.strategy_tabulator, name='strategy_tabulator'),
    
    path('order/place/', views.place_order_view, name='place_order_view'),
    
    path('asset-tradable/', views.asset_search_tabulator, name='asset_tradable_home'),  # Redirection vers la recherche
    path('asset-tradable/<int:asset_tradable_id>/update-saxo/', views.update_asset_tradable_saxo, name='update_asset_tradable_saxo'),
    path('asset-tradable/update-all-saxo/', views.update_all_saxo_assets, name='update_all_saxo_assets'),
    path('asset-tradable/update-saxo-page/', views.update_saxo_assets_page, name='update_saxo_assets_page'),
]