from django.core.management.base import BaseCommand
from decimal import Decimal
from cocktails_app.models import Category, Ingredient, Cocktail, CocktailIngredient, Promotion


class Command(BaseCommand):
    help = "Peuple la boutique de cocktails avec des données de démo"

    def handle(self, *args, **options):
        self.stdout.write("Création catégories…")
        classics, _ = Category.objects.get_or_create(name="Classiques", defaults={"description": "Les incontournables"})
        signatures, _ = Category.objects.get_or_create(name="Signatures", defaults={"description": "Nos créations"})
        softs, _ = Category.objects.get_or_create(name="Sans alcool")

        self.stdout.write("Création ingrédients…")
        rum, _ = Ingredient.objects.get_or_create(name="Rhum blanc", defaults={"default_unit": "ml", "is_alcohol": True})
        tequila, _ = Ingredient.objects.get_or_create(name="Tequila", defaults={"default_unit": "ml", "is_alcohol": True})
        lime, _ = Ingredient.objects.get_or_create(name="Jus de citron vert", defaults={"default_unit": "ml"})
        sugar, _ = Ingredient.objects.get_or_create(name="Sirop de sucre", defaults={"default_unit": "ml"})
        mint, _ = Ingredient.objects.get_or_create(name="Menthe", defaults={"default_unit": "pcs"})
        soda, _ = Ingredient.objects.get_or_create(name="Eau gazeuse", defaults={"default_unit": "ml"})
        cointreau, _ = Ingredient.objects.get_or_create(name="Cointreau", defaults={"default_unit": "ml", "is_alcohol": True})
        pineapple, _ = Ingredient.objects.get_or_create(name="Jus d'ananas", defaults={"default_unit": "ml"})
        coconut, _ = Ingredient.objects.get_or_create(name="Lait de coco", defaults={"default_unit": "ml"})

        self.stdout.write("Création cocktails…")
        mojito, _ = Cocktail.objects.get_or_create(
            name="Mojito",
            defaults={
                "category": classics,
                "description": "Rhum, menthe, citron vert, sucre, eau gazeuse",
                "price": Decimal("8.50"),
                "is_alcoholic": True,
                "popularity": 100,
            },
        )
        margarita, _ = Cocktail.objects.get_or_create(
            name="Margarita",
            defaults={
                "category": classics,
                "description": "Tequila, cointreau, citron vert",
                "price": Decimal("9.50"),
                "is_alcoholic": True,
                "popularity": 90,
            },
        )
        pina, _ = Cocktail.objects.get_or_create(
            name="Piña Colada",
            defaults={
                "category": classics,
                "description": "Rhum, jus d'ananas, lait de coco",
                "price": Decimal("9.00"),
                "is_alcoholic": True,
                "popularity": 85,
            },
        )
        virgin, _ = Cocktail.objects.get_or_create(
            name="Virgin Mojito",
            defaults={
                "category": softs,
                "description": "Menthe, citron vert, sucre, eau gazeuse",
                "price": Decimal("6.50"),
                "is_alcoholic": False,
                "popularity": 70,
            },
        )

        def set_recipe(c, items):
            for ing, qty, unit, note in items:
                CocktailIngredient.objects.get_or_create(
                    cocktail=c, ingredient=ing,
                    defaults={"quantity": Decimal(str(qty)), "unit": unit, "note": note}
                )

        set_recipe(mojito, [
            (rum, 50, "ml", ""), (lime, 25, "ml", ""), (sugar, 15, "ml", ""), (mint, 8, "pcs", "feuilles"), (soda, 100, "ml", "compléter")
        ])
        set_recipe(margarita, [
            (tequila, 50, "ml", ""), (cointreau, 20, "ml", ""), (lime, 25, "ml", "")
        ])
        set_recipe(pina, [
            (rum, 40, "ml", ""), (pineapple, 120, "ml", ""), (coconut, 40, "ml", "")
        ])
        set_recipe(virgin, [
            (lime, 25, "ml", ""), (sugar, 15, "ml", ""), (mint, 8, "pcs", "feuilles"), (soda, 120, "ml", "compléter")
        ])

        Promotion.objects.get_or_create(code="WELCOME10", defaults={"description": "-10% de bienvenue", "percentage": Decimal("10.0"), "active": True})

        self.stdout.write(self.style.SUCCESS("Données cocktails créées."))