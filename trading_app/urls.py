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
    path('trades/tabulator/synch/', views.trade_tabulator_with_synch, name='trade_tabulator_with_synch'),
    path('trades/binance/', views.binance_trades_ajax, name='binance_trades_ajax'),
    path('trades/delete-all/', views.delete_all_trades, name='delete_all_trades'),
    path('trades/update-all/', views.update_all_trades, name='update_all_trades'),
    path('trades/chart-data/<str:asset_symbol>/', views.get_asset_price_for_chart, name='get_asset_price_for_chart'),
    path('pending-orders/tabulator/', views.pending_orders_tabulator, name='pending_orders_tabulator'),
    path('sync-pending-orders/<int:broker_id>/', views.sync_pending_orders, name='sync_pending_orders'),
    path('cancel-order/<str:order_id>/', views.cancel_order, name='cancel_order'),
    
    path('positions/tabulator/', views.position_tabulator, name='position_tabulator'),
    path('positions/binance/', views.binance_positions_ajax, name='binance_positions_ajax'),
    path('positions/delete-all/', views.delete_all_positions, name='delete_all_positions'),
    path('positions/update-all/', views.update_all_positions, name='update_all_positions'),

    path('assets/sync-all/', views.sync_all_assets, name='sync_all_assets'),
    path('brokers/<int:broker_id>/sync-assets/', views.sync_broker_assets, name='sync_broker_assets'),
    path('assets/search/', views.search_all_assets, name='search_all_assets'),
    

    path('assets/tabulator/', views.asset_tabulator, name='asset_tabulator'),
    path('assets/save/', views.save_asset_ajax, name='save_asset_ajax'),
    path('assets/tradable/tabulator/', views.asset_tradable_tabulator, name='asset_tradable_tabulator'),
    path('assets/search/tabulator/', views.asset_search_tabulator, name='asset_search_tabulator'),
    path('assets/update-yahoo/', views.update_all_assets_with_yahoo, name='update_all_assets_with_yahoo'),
    path('assets/autocomplete/', views.asset_autocomplete, name='asset_autocomplete'),
    path('assets/create/', views.create_asset, name='create_asset'),
    path('assets/<int:asset_id>/price-history/', views.get_asset_price_history, name='get_asset_price_history'),
    path('assets/<int:asset_id>/price/', views.get_asset_price, name='get_asset_price'),
    path('brokers/<int:broker_id>/balance/', views.get_broker_balance, name='get_broker_balance'),
    
    path('strategies/tabulator/', views.strategy_tabulator, name='strategy_tabulator'),
    path('strategies/create/', views.create_strategy, name='create_strategy'),
    path('strategies/<int:strategy_id>/details/', views.strategy_details, name='strategy_details'),
    path('strategies/<int:strategy_id>/toggle/', views.toggle_strategy, name='toggle_strategy'),
    path('strategies/<int:strategy_id>/delete/', views.delete_strategy, name='delete_strategy'),
    path('strategies/<int:strategy_id>/execute/', views.execute_strategy, name='execute_strategy'),
    path('strategies/<int:strategy_id>/update-frequency/', views.update_strategy_frequency, name='update_strategy_frequency'),
    path('strategies/<int:strategy_id>/update/', views.update_strategy, name='update_strategy'),
    path('strategies/execution-history/', views.execution_history, name='execution_history'),
    
    path('order/place/', views.place_order_view, name='place_order_view'),
    
    path('asset-tradable/', views.asset_search_tabulator, name='asset_tradable_home'),  # Redirection vers la recherche
    path('asset-tradable/<int:asset_tradable_id>/update-saxo/', views.update_asset_tradable_saxo, name='update_asset_tradable_saxo'),
    path('asset-tradable/update-all-saxo/', views.update_all_saxo_assets, name='update_all_saxo_assets'),
    path('asset-tradable/update-saxo-page/', views.update_saxo_assets_page, name='update_saxo_assets_page'),
    path('kenza/', views.kenza, name='kenza'),
    path('test/', views.test_page, name='test_page'),
]