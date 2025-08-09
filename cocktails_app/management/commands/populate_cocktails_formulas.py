from django.core.management.base import BaseCommand
from django.db import transaction

from cocktails_app.models import Category, Cocktail, Formula, FormulaCocktail


class Command(BaseCommand):
    help = "Create 13 cocktails (if missing) and 4 formulas with their descriptions."

    def handle(self, *args, **options):
        with transaction.atomic():
            # Ensure a default category exists
            cat, _ = Category.objects.get_or_create(name="Signatures", defaults={"description": "Cocktails signatures"})

            # 13 cocktails to fuel the formulas
            cocktail_names = [
                "Mojito Classique",
                "Mojito Fraise",
                "Daiquiri",
                "Piña Colada",
                "Margarita",
                "Cosmopolitan",
                "Old Fashioned",
                "Whisky Sour",
                "Negroni",
                "Moscow Mule",
                "Gin Tonic",
                "Tequila Sunrise",
                "Spritz",
            ]

            cocktails = []
            for name in cocktail_names:
                c, _ = Cocktail.objects.get_or_create(
                    name=name,
                    defaults={
                        "category": cat,
                        "description": f"{name} — ajouté automatiquement pour les formules",
                        "price": 9.90,
                        "is_alcoholic": True,
                        "popularity": 50,
                    },
                )
                cocktails.append(c)

            # Create formulas
            f1, _ = Formula.objects.get_or_create(
                name="Formule 1",
                defaults={
                    "title": "Formule tête à tête",
                    "definition": "2 personnes : 1 petite bouteille spiritueux",
                    "quantity_text": "Spiritueux = 30cl → 6 verres de 5cl",
                    "cost_text": "Ça va couter cher",
                    "description": "Petits cocktails romantiques",
                },
            )

            f2, _ = Formula.objects.get_or_create(
                name="Formule 2",
                defaults={
                    "title": "Formule amitié",
                    "definition": "7 personnes : 1 bouteille de spiritueux",
                    "quantity_text": "Spiritueux = 70cl → 14 verres de 5cl",
                    "cost_text": "Ça va couter encore plus cher. Pas de prix d'ami",
                    "description": "Formule standard",
                },
            )

            f3, _ = Formula.objects.get_or_create(
                name="Formule 3",
                defaults={
                    "title": "Formule découverte",
                    "definition": "7 personnes : 1 bouteille de spiritueux",
                    "quantity_text": "Spiritueux = 70cl → 14 verres de 5cl",
                    "cost_text": "Le prix aussi ça va être une découverte",
                    "description": "Formule standard avec alcool en reste (équilibrer les stocks)",
                },
            )

            f4, _ = Formula.objects.get_or_create(
                name="Formule 4",
                defaults={
                    "title": "Formule Creator/Signature",
                    "definition": "10 personnes : 2 bouteilles de spiritueux",
                    "quantity_text": "",
                    "cost_text": "",
                    "description": "On envoie un assortiment et le client crée. Rapport quantité/prix intéressant; vide les stocks.",
                },
            )

            # Attach a small selection of cocktails to each formula
            mapping = {
                f1: ["Mojito Classique", "Daiquiri", "Cosmopolitan"],
                f2: ["Margarita", "Piña Colada", "Whisky Sour", "Moscow Mule"],
                f3: ["Negroni", "Old Fashioned", "Spritz", "Gin Tonic"],
                f4: ["Tequila Sunrise", "Mojito Fraise", "Moscow Mule", "Spritz"],
            }

            for formula, names in mapping.items():
                for nm in names:
                    c = Cocktail.objects.get(name=nm)
                    FormulaCocktail.objects.get_or_create(formula=formula, cocktail=c, defaults={"servings": 1})

        self.stdout.write(self.style.SUCCESS("Formules et 13 cocktails prêts."))

