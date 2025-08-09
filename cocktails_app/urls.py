from django.urls import path
from . import views

app_name = "cocktails_app"

urlpatterns = [
    path("", views.home, name="home"),
    path("c/<slug:slug>/", views.cocktail_detail, name="cocktail_detail"),
    path("add-to-cart/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.view_cart, name="view_cart"),
    path("cart/update/", views.update_cart, name="update_cart"),
    path("cart/remove/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/success/<int:order_id>/", views.order_success, name="order_success"),
    path("formules/", views.formulas_list, name="formulas"),
]