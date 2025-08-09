from django.core.management.base import BaseCommand
from cocktails_app.models import Ingredient


LINKS = {
    "Rhum": "https://www.lepetitballon.com/spirits/rhum.html",
    "Vodka": "https://www.lepetitballon.com/spirits/vodka.html",
    "Gin": "https://www.lepetitballon.com/spirits/gin.html",
    "Tequila": "https://www.lepetitballon.com/spirits/tequila.html",
    "Baileys": "https://www.vinatis.com/39029-baileys-original-irish-cream",
    "Cointreau": "https://www.vinatis.com/13049-cointreau",
    "Liqueur de café": "https://www.vinatis.com/39278-kahlua-liqueur-de-cafe",
    "Champagne": "https://www.vinatis.com/champagne",
    "Menthe": "https://www.parismarche.fr/marches/aligre",
    "Pamplemousse": "https://www.mon-marche.fr/fr/produit/pamplemousse-rose",
    "Concombre": "https://www.mon-marche.fr/fr/produit/concombre",
    "Citron vert": "https://www.mon-marche.fr/fr/produit/citron-vert",
    "Sirop de sucre": "https://www.monin.com/fr/sirop-sucre-de-canne.html",
    "Sirop fraise": "https://www.monin.com/fr/sirop-fraise.html",
    "Sirop rose": "https://www.monin.com/fr/sirop-rose.html",
    "Sirop menthe": "https://www.monin.com/fr/sirop-menthe-verte.html",
    "Sirop coco": "https://www.monin.com/fr/sirop-noix-de-coco.html",
    "Limonade": "https://www.nature-et-decouvertes.com/epicerie/boissons/",
    "Eau gazeuse": "https://www.carrefour.fr/p/eau-gazeuse-san-pellegrino-8002270120047",
    "Tonic": "https://www.fevetree.com/fr/products/premium-indian-tonic-water",
    "Purée de pêche": "https://www.capfruit.com/fr/nos-produits/nos-purees",
    "Jus d’ananas": "https://www.monoprix.fr/courses/jus-ananas-pure-jus-monoprix-1l--3650881-p",
    "Myrtilles": "https://www.mon-marche.fr/fr/produit/myrtille",
    "Gingembre": "https://www.mon-marche.fr/fr/produit/gingembre",
    "Pétales": "https://www.cuisineaddict.com/achat-fleurs-comestibles-508.htm",
}


class Command(BaseCommand):
    help = "Met à jour les ingrédients avec des liens d'achat externes"

    def handle(self, *args, **options):
        updated = 0
        for name, url in LINKS.items():
            # Chercher exact et variantes simples (ex: 'Jus d’ananas' vs 'Jus d'ananas')
            candidates = Ingredient.objects.filter(name__iexact=name)
            if not candidates.exists():
                if name == "Jus d’ananas":
                    candidates = Ingredient.objects.filter(name__iexact="Jus d'ananas")
            for ing in candidates:
                ing.buy_link = url
                ing.save(update_fields=["buy_link"])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Liens mis à jour pour {updated} ingrédients."))