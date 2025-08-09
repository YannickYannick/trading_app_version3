from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal

from .models import Category, Ingredient, Cocktail, CocktailIngredient, Order, OrderItem, Promotion, Formula


def _get_or_create_cart(request: HttpRequest) -> Order:
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    order, _ = Order.objects.get_or_create(session_key=session_key, status=Order.STATUS_CART)
    if request.user.is_authenticated and order.user is None:
        order.user = request.user
        order.save()
    return order


def home(request: HttpRequest):
    """Liste des cocktails avec filtres et recherche"""
    cocktails = Cocktail.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)

    q = request.GET.get("q")
    cat = request.GET.get("cat")
    alc = request.GET.get("alc")
    sort = request.GET.get("sort", "popularity")
    price_min = request.GET.get("price_min")
    price_max = request.GET.get("price_max")
    stock = request.GET.get("stock")  # "in" or "out"
    alcohol = request.GET.get("alcohol")  # ingredient id

    if q:
        cocktails = cocktails.filter(name__icontains=q)
    if cat:
        cocktails = cocktails.filter(category__slug=cat)
    if alc in {"yes", "no"}:
        cocktails = cocktails.filter(is_alcoholic=(alc == "yes"))
    if price_min:
        try:
            cocktails = cocktails.filter(price__gte=Decimal(price_min))
        except Exception:
            pass
    if price_max:
        try:
            cocktails = cocktails.filter(price__lte=Decimal(price_max))
        except Exception:
            pass
    if stock == "in":
        cocktails = cocktails.filter(is_active=True)
    elif stock == "out":
        cocktails = cocktails.filter(is_active=False)

    # Filtre par type d'alcool (ingrédient)
    if alcohol:
        try:
            cocktails = cocktails.filter(recipe_items__ingredient__id=int(alcohol))
        except Exception:
            pass

    if sort == "price":
        cocktails = cocktails.order_by("price")
    elif sort == "name":
        cocktails = cocktails.order_by("name")
    else:
        cocktails = cocktails.order_by("-popularity")

    # Liste des alcools disponibles (marqués alcool OU noms connus), utilisés dans au moins une recette
    alcohol_q = (
        Q(is_alcohol=True)
        | Q(name__icontains="rhum")
        | Q(name__icontains="rum")
        | Q(name__icontains="vodka")
        | Q(name__icontains="gin")
        | Q(name__icontains="tequila")
        | Q(name__icontains="whisky")
        | Q(name__icontains="whiskey")
        | Q(name__icontains="bourbon")
        | Q(name__icontains="cognac")
        | Q(name__icontains="champagne")
        | Q(name__icontains="liqueur")
        | Q(name__icontains="cointreau")
        | Q(name__icontains="baileys")
    )
    alcohol_types_qs = Ingredient.objects.filter(alcohol_q, used_in__isnull=False).order_by("name").distinct()

    # Serialize for React (avoid passing QuerySet to json_script)
    cocktails_data = [
        {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "price": float(c.price),
            "is_alcoholic": bool(c.is_alcoholic),
            "image_url_or_placeholder": c.image_url_or_placeholder,
        }
        for c in cocktails
    ]

    categories_data = [
        {"id": cat.id, "name": cat.name, "slug": cat.slug}
        for cat in categories
    ]
    alcohol_types_data = [
        {"id": ing.id, "name": ing.name}
        for ing in alcohol_types_qs
    ]

    context = {
        "cocktails": cocktails,
        "cocktails_data": cocktails_data,
        "categories": categories,
        "alcohol_types": alcohol_types_qs,
        "filters": {
            "q": q or "",
            "cat": cat or "",
            "alc": alc or "",
            "sort": sort,
            "price_min": price_min or "",
            "price_max": price_max or "",
            "stock": stock or "",
            "alcohol": alcohol or "",
        },
        "categories_data": categories_data,
        "alcohol_types_data": alcohol_types_data,
    }
    return render(request, "cocktails_app/home.html", context)


def cocktail_detail(request: HttpRequest, slug: str):
    cocktail = get_object_or_404(Cocktail, slug=slug, is_active=True)
    recipe = cocktail.recipe_items.select_related("ingredient")
    return render(request, "cocktails_app/cocktail_detail.html", {"cocktail": cocktail, "recipe": recipe})


@require_POST
@transaction.atomic
def add_to_cart(request: HttpRequest):
    order = _get_or_create_cart(request)
    cocktail_id = request.POST.get("cocktail_id")
    qty = int(request.POST.get("quantity", 1))
    cocktail = get_object_or_404(Cocktail, id=cocktail_id, is_active=True)

    item, created = OrderItem.objects.get_or_create(
        order=order, cocktail=cocktail, defaults={"quantity": qty, "unit_price": cocktail.price}
    )
    if not created:
        item.quantity += qty
        item.save()

    messages.success(request, f"{cocktail.name} ajouté au panier")
    return redirect("cocktails_app:view_cart")


def view_cart(request: HttpRequest):
    order = _get_or_create_cart(request)
    return render(request, "cocktails_app/cart.html", {"order": order})


@require_POST
def update_cart(request: HttpRequest):
    order = _get_or_create_cart(request)
    for item in order.items.select_related("cocktail"):
        new_qty = int(request.POST.get(f"qty_{item.id}", item.quantity))
        if new_qty <= 0:
            item.delete()
        else:
            item.quantity = new_qty
            item.save()
    messages.success(request, "Panier mis à jour")
    return redirect("cocktails_app:view_cart")


@require_POST
def remove_from_cart(request: HttpRequest):
    order = _get_or_create_cart(request)
    item_id = request.POST.get("item_id")
    order.items.filter(id=item_id).delete()
    messages.info(request, "Article retiré du panier")
    return redirect("cocktails_app:view_cart")


@transaction.atomic
def checkout(request: HttpRequest):
    order = _get_or_create_cart(request)
    if request.method == "POST":
        order.customer_name = request.POST.get("name", "")
        order.customer_email = request.POST.get("email", "")
        order.customer_phone = request.POST.get("phone", "")
        order.delivery_address = request.POST.get("address", "")
        promo_code = request.POST.get("promo", "").strip()

        if promo_code:
            promo = Promotion.objects.filter(code__iexact=promo_code, active=True).first()
            if promo:
                order.promotion = promo
                messages.success(request, f"Code promo {promo.code} appliqué")
            else:
                order.promotion = None
                messages.warning(request, "Code promo invalide")

        # Simulation de paiement: passage en payé directement
        order.status = Order.STATUS_PAID
        order.save()
        messages.success(request, "Commande validée !")
        return redirect("cocktails_app:order_success", order_id=order.id)

    return render(request, "cocktails_app/checkout.html", {"order": order})


def order_success(request: HttpRequest, order_id: int):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "cocktails_app/order_success.html", {"order": order})


def formulas_list(request: HttpRequest):
    formulas_qs = Formula.objects.filter(is_active=True).prefetch_related("formula_items__cocktail")
    # Serialize minimal structure for React
    formulas = []
    for f in formulas_qs:
        items = []
        for it in f.formula_items.all():
            items.append({
                "cocktail_id": it.cocktail_id,
                "cocktail_name": it.cocktail.name,
                "servings": it.servings,
            })
        formulas.append({
            "id": f.id,
            "name": f.name,
            "title": f.title,
            "definition": f.definition,
            "quantity_text": f.quantity_text,
            "cost_text": f.cost_text,
            "description": f.description,
            "formula_items": items,
        })
    return render(request, "cocktails_app/formulas.html", {"formulas": formulas})