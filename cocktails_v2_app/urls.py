from django.urls import path
from . import views

app_name = "cocktails_v2_app"

urlpatterns = [
    path("", views.home, name="home"),
    path("p/<slug:slug>/", views.product_detail, name="product_detail"),
    path("add/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.view_cart, name="view_cart"),
    path("cart/update/", views.update_cart, name="update_cart"),
    path("cart/remove/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("success/<int:order_id>/", views.order_success, name="order_success"),
]