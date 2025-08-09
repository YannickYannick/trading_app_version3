from django.core.management.base import BaseCommand
from decimal import Decimal
from cocktails_v2_app.models import (
    Tag, Category, InventoryItem, Product, ProductVariant,
    OptionGroup, Option, RecipeItem, HappyHour
)


class Command(BaseCommand):
    help = "Peuple Cocktails V2 avec des données de démo"

    def handle(self, *args, **options):
        fresh, _ = Tag.objects.get_or_create(name="Frais")
        spicy, _ = Tag.objects.get_or_create(name="Epicé")
        classic, _ = Category.objects.get_or_create(name="Classiques")
        sig, _ = Category.objects.get_or_create(name="Signatures")

        rum, _ = InventoryItem.objects.get_or_create(name="Rhum blanc", defaults={"unit": "ml", "is_alcohol": True, "current_quantity": Decimal("5000")})
        lime, _ = InventoryItem.objects.get_or_create(name="Jus de citron vert", defaults={"unit": "ml", "current_quantity": Decimal("5000")})
        sugar, _ = InventoryItem.objects.get_or_create(name="Sirop de sucre", defaults={"unit": "ml", "current_quantity": Decimal("3000")})
        mint, _ = InventoryItem.objects.get_or_create(name="Menthe", defaults={"unit": "pcs", "current_quantity": Decimal("200")})
        soda, _ = InventoryItem.objects.get_or_create(name="Eau gazeuse", defaults={"unit": "ml", "current_quantity": Decimal("5000")})

        mojito, _ = Product.objects.get_or_create(name="Mojito", defaults={"category": classic, "base_price": Decimal("8.00"), "is_alcoholic": True})
        mojito.tags.add(fresh)
        ProductVariant.objects.get_or_create(product=mojito, name="Medium", defaults={"size": "M", "price": Decimal("8.00")})
        ProductVariant.objects.get_or_create(product=mojito, name="Large", defaults={"size": "L", "price": Decimal("9.50")})

        RecipeItem.objects.get_or_create(product=mojito, inventory_item=rum, defaults={"quantity": Decimal("50"), "unit": "ml"})
        RecipeItem.objects.get_or_create(product=mojito, inventory_item=lime, defaults={"quantity": Decimal("25"), "unit": "ml"})
        RecipeItem.objects.get_or_create(product=mojito, inventory_item=sugar, defaults={"quantity": Decimal("15"), "unit": "ml"})
        RecipeItem.objects.get_or_create(product=mojito, inventory_item=mint, defaults={"quantity": Decimal("8"), "unit": "pcs"})
        RecipeItem.objects.get_or_create(product=mojito, inventory_item=soda, defaults={"quantity": Decimal("100"), "unit": "ml"})

        base_group, _ = OptionGroup.objects.get_or_create(product=mojito, name="Base alcool", defaults={"required": True, "max_choices": 1})
        Option.objects.get_or_create(group=base_group, name="Rhum blanc", defaults={"price_delta": Decimal("0.00")})
        Option.objects.get_or_create(group=base_group, name="Rhum ambré", defaults={"price_delta": Decimal("0.50")})

        HappyHour.objects.get_or_create(name="Happy Hour Soir", defaults={"discount_percent": Decimal("20.0"), "weekday": 4, "start_time": "18:00", "end_time": "20:00", "active": True})

        self.stdout.write(self.style.SUCCESS("Cocktails V2: données créées."))