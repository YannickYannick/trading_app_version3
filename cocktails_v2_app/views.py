from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from decimal import Decimal
from .models import (
    Tag, Category, Product, ProductVariant, OptionGroup, Option,
    Order, OrderItem
)


def _get_or_create_cart(request):
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    order, _ = Order.objects.get_or_create(session_key=session_key, status="cart")
    if request.user.is_authenticated and order.user is None:
        order.user = request.user
        order.save()
    return order


def home(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)
    tags = Tag.objects.all()

    q = request.GET.get("q")
    cat = request.GET.get("cat")
    tag = request.GET.get("tag")
    sort = request.GET.get("sort", "name")

    if q:
        products = products.filter(name__icontains=q)
    if cat:
        products = products.filter(category__slug=cat)
    if tag:
        products = products.filter(tags__slug=tag)

    if sort == "price":
        products = products.order_by("base_price")
    elif sort == "name":
        products = products.order_by("name")
    else:
        products = products.order_by("-id")

    return render(request, "cocktails_v2_app/home.html", {
        "products": products,
        "categories": categories,
        "tags": tags,
        "filters": {"q": q or "", "cat": cat or "", "tag": tag or "", "sort": sort}
    })


def product_detail(request, slug: str):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    variants = product.variants.all()
    groups = product.option_groups.prefetch_related("options").all()
    return render(request, "cocktails_v2_app/product_detail.html", {
        "product": product,
        "variants": variants,
        "groups": groups,
    })


@require_POST
def add_to_cart(request):
    order = _get_or_create_cart(request)
    product_id = request.POST.get("product_id")
    variant_id = request.POST.get("variant_id")
    qty = int(request.POST.get("quantity", 1))

    product = get_object_or_404(Product, id=product_id)
    variant = ProductVariant.objects.filter(id=variant_id).first() if variant_id else None

    unit_price = variant.price if variant else product.base_price
    item = OrderItem.objects.create(order=order, product=product, variant=variant, quantity=qty, unit_price=unit_price)

    # options
    option_ids = request.POST.getlist("options")
    if option_ids:
        options = Option.objects.filter(id__in=option_ids)
        item.selected_options.set(options)

    messages.success(request, "Ajouté au panier")
    return redirect("cocktails_v2_app:view_cart")


def view_cart(request):
    order = _get_or_create_cart(request)
    return render(request, "cocktails_v2_app/cart.html", {"order": order})


@require_POST
def update_cart(request):
    order = _get_or_create_cart(request)
    for item in order.items.select_related("product"):
        new_qty = int(request.POST.get(f"qty_{item.id}", item.quantity))
        if new_qty <= 0:
            item.delete()
        else:
            item.quantity = new_qty
            item.save()
    messages.success(request, "Panier mis à jour")
    return redirect("cocktails_v2_app:view_cart")


@require_POST
def remove_from_cart(request):
    order = _get_or_create_cart(request)
    item_id = request.POST.get("item_id")
    order.items.filter(id=item_id).delete()
    messages.info(request, "Article retiré")
    return redirect("cocktails_v2_app:view_cart")


def checkout(request):
    order = _get_or_create_cart(request)
    if request.method == "POST":
        order.customer_name = request.POST.get("name", "")
        order.table_number = request.POST.get("table", "")
        order.status = "paid"  # simulation de paiement
        order.save()
        messages.success(request, "Commande validée !")
        return redirect("cocktails_v2_app:order_success", order_id=order.id)
    return render(request, "cocktails_v2_app/checkout.html", {"order": order})


def order_success(request, order_id: int):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "cocktails_v2_app/order_success.html", {"order": order})