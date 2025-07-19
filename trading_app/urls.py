from django.urls import path
from .views import asset_list, asset_tabulator, save_asset_ajax

urlpatterns = [
    path('assets/', asset_list, name='asset_list'),
    path('assets/tabulator/', asset_tabulator, name='asset_tabulator'),
    path('assets/save/', save_asset_ajax, name='save_asset_ajax'),
] 