from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings
from cocktails_app.models import Cocktail
import requests
import os

UNSPLASH_URL = "https://source.unsplash.com/800x600/?cocktail,{query}"

class Command(BaseCommand):
    help = "Télécharge des images pour les cocktails (placeholder Unsplash) et les associe"

    def handle(self, *args, **options):
        count = 0
        for c in Cocktail.objects.all():
            if c.image:
                continue
            url = UNSPLASH_URL.format(query=c.name.replace(" ", "+"))
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    filename = f"cocktail_{c.id}.jpg"
                    c.image.save(filename, ContentFile(resp.content), save=True)
                    count += 1
            except Exception:
                continue
        self.stdout.write(self.style.SUCCESS(f"Images ajoutées: {count}"))