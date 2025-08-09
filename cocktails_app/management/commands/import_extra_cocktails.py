from django.core.management.base import BaseCommand
from decimal import Decimal
from cocktails_app.models import Category, Ingredient, Cocktail, CocktailIngredient
import re


DATA = [
    {
        "name": "Mojito Rouge au Pamplemousse",
        "ingredients": ["Rhum blanc", "Pamplemousse", "Menthe", "Limonade", "Sirop de sucre"],
        "quantities": ["15cl", "20cl", "10g", "25cl", "5cl"],
        "price": Decimal("8.50"),
    },
    {
        "name": "Tequila Concombre Fresh",
        "ingredients": ["Tequila", "Concombre", "Menthe", "Citron vert", "Sirop de sucre", "Eau gazeuse"],
        "quantities": ["8cl", "1/2", "10g", "3cl", "4cl", "25cl"],
        "price": Decimal("7.80"),
    },
    {
        "name": "Champagne Pêche",
        "ingredients": ["Champagne", "Purée de pêche", "Citron vert", "Gin"],
        "quantities": ["25cl", "10cl", "1/2", "6cl"],
        "price": Decimal("10.50"),
    },
    {
        "name": "Pink Lime Rhum",
        "ingredients": ["Rhum blanc", "Sirop rose", "Citron vert", "Eau gazeuse"],
        "quantities": ["10cl", "5cl", "1", "25cl"],
        "price": Decimal("6.90"),
    },
    {
        "name": "B-52",
        "ingredients": ["Liqueur de café", "Baileys", "Cointreau"],
        "quantities": ["6cl", "6cl", "6cl"],
        "price": Decimal("9.00"),
    },
    {
        "name": "Tropical Twist",
        "ingredients": ["Rhum ambré", "Jus d’ananas", "Sirop coco", "Gingembre"],
        "quantities": ["10cl", "20cl", "5cl", "5g"],
        "price": Decimal("7.60"),
    },
    {
        "name": "Berry Bomb",
        "ingredients": ["Vodka", "Sirop de fraise", "Citron vert", "Eau gazeuse", "Myrtilles"],
        "quantities": ["10cl", "5cl", "1", "25cl", "30g"],
        "price": Decimal("8.30"),
    },
    {
        "name": "Mentha Glacialis",
        "ingredients": ["Gin", "Sirop de menthe", "Tonic"],
        "quantities": ["10cl", "4cl", "25cl"],
        "price": Decimal("7.50"),
    },
    {
        "name": "Signature DIY",
        "ingredients": ["Rhum blanc", "Gin", "Vodka", "Sirops (assortiment)", "Jus (assortiment)", "Déco"],
        "quantities": ["3x5cl", "3x5cl", "3x5cl", "3x5cl", "2x10cl", "1"],
        "price": Decimal("11.00"),
    },
    {
        "name": "Rose de Minuit",
        "ingredients": ["Vodka à la rose", "Sirop de litchi", "Citron", "Eau gazeuse", "Pétales"],
        "quantities": ["10cl", "5cl", "1", "25cl", "2g"],
        "price": Decimal("9.80"),
    },
]

ALIASES = {
    "Rhum": "Rhum blanc",
    "Eau pétillante": "Eau gazeuse",
    "Citron": "Citron vert",
    "Sirop coco": "Sirop de coco",
    "Sirop de fraise": "Sirop fraise",
}


def parse_quantity(token: str):
    token = token.strip().lower()
    # Forms: '10cl', '5g', '1/2', '1', '3x5cl', '2x10cl'
    m = re.match(r"^(\d+)x(\d+)(ml|cl|g|l)$", token)
    if m:
        times = int(m.group(1))
        amount = int(m.group(2))
        unit = m.group(3)
        return Decimal(str(times * amount)), unit
    m = re.match(r"^(\d+)(ml|cl|g|l)$", token)
    if m:
        return Decimal(m.group(1)), m.group(2)
    if token in {"1/2", "0.5"}:
        return Decimal("0.5"), "pcs"
    if re.match(r"^\d+$", token):
        return Decimal(token), "pcs"
    # Fallback
    return Decimal("0"), "pcs"


class Command(BaseCommand):
    help = "Importe une liste de cocktails additionnels avec ingrédients et quantités"

    def handle(self, *args, **options):
        signatures, _ = Category.objects.get_or_create(name="Signatures", defaults={"description": "Recettes spéciales"})
        created = 0
        updated = 0
        for row in DATA:
            name = row["name"].strip()
            ingredients = [ALIASES.get(x.strip(), x.strip()) for x in row["ingredients"]]
            quantities = [q.strip() for q in row["quantities"]]
            price = row["price"]

            cocktail, was_created = Cocktail.objects.get_or_create(
                name=name,
                defaults={
                    "category": signatures,
                    "description": "Ajouté via import personnalisé",
                    "price": price,
                    "is_alcoholic": True,
                },
            )
            if not was_created:
                cocktail.category = signatures
                cocktail.price = price
                cocktail.save()
                updated += 1
            else:
                created += 1

            # Clear existing recipe if any, then rebuild
            CocktailIngredient.objects.filter(cocktail=cocktail).delete()

            for ing_name, qty_token in zip(ingredients, quantities):
                qty, unit = parse_quantity(qty_token)
                ing, _ = Ingredient.objects.get_or_create(name=ing_name)
                # If we have a sensible default unit, keep; else use parsed unit
                CocktailIngredient.objects.create(
                    cocktail=cocktail,
                    ingredient=ing,
                    quantity=qty,
                    unit=unit,
                )

        self.stdout.write(self.style.SUCCESS(f"Import terminé. Créés: {created}, Mis à jour: {updated}"))