#!/usr/bin/env python3
"""
Script pour générer automatiquement toutes les icônes PWA nécessaires
à partir d'une icône de base (recommandé: 512x512 pixels)

Usage: python generate_pwa_icons.py
"""

import os
from PIL import Image, ImageDraw, ImageFont
import math

def create_icon(size, text="TA", bg_color="#007bff", text_color="white"):
    """Créer une icône carrée avec du texte"""
    # Créer une image carrée
    img = Image.new('RGBA', (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Calculer la taille de la police (environ 1/3 de la taille de l'image)
    font_size = max(12, size // 3)
    
    try:
        # Essayer d'utiliser une police système
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except:
            # Police par défaut
            font = ImageFont.load_default()
    
    # Centrer le texte
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    # Dessiner le texte
    draw.text((x, y), text, fill=text_color, font=font)
    
    return img

def create_maskable_icon(size, text="TA", bg_color="#007bff", text_color="white"):
    """Créer une icône maskable (avec zone de sécurité)"""
    # Créer une image carrée
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Zone de sécurité (80% de la taille totale)
    safe_zone = int(size * 0.8)
    offset = (size - safe_zone) // 2
    
    # Dessiner le fond dans la zone de sécurité
    draw.rectangle([offset, offset, offset + safe_zone, offset + safe_zone], 
                  fill=bg_color)
    
    # Calculer la taille de la police
    font_size = max(12, safe_zone // 3)
    
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    # Centrer le texte dans la zone de sécurité
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = offset + (safe_zone - text_width) // 2
    y = offset + (safe_zone - text_height) // 2
    
    # Dessiner le texte
    draw.text((x, y), text, fill=text_color, font=font)
    
    return img

def main():
    """Fonction principale"""
    print("🎨 Génération des icônes PWA pour Trading App...")
    
    # Créer le dossier static/icons s'il n'existe pas
    icons_dir = "trading_app/static/icons"
    os.makedirs(icons_dir, exist_ok=True)
    
    # Tailles d'icônes requises pour PWA
    icon_sizes = [
        16, 32, 72, 96, 128, 144, 152, 192, 384, 512
    ]
    
    # Icônes spéciales
    special_icons = {
        "badge-72x72": 72,
        "open-96x96": 96,
        "close-96x96": 96,
        "strategy-96x96": 96,
        "broker-96x96": 96,
        "position-96x96": 96
    }
    
    # Couleurs pour les icônes spéciales
    special_colors = {
        "badge-72x72": "#dc3545",  # Rouge pour les notifications
        "open-96x96": "#28a745",   # Vert pour ouvrir
        "close-96x96": "#6c757d",  # Gris pour fermer
        "strategy-96x96": "#007bff", # Bleu pour les stratégies
        "broker-96x96": "#ffc107",   # Jaune pour les brokers
        "position-96x96": "#17a2b8"  # Cyan pour les positions
    }
    
    # Générer les icônes principales
    print("📱 Génération des icônes principales...")
    for size in icon_sizes:
        filename = f"icon-{size}x{size}.png"
        filepath = os.path.join(icons_dir, filename)
        
        # Créer l'icône
        icon = create_icon(size, "TA", "#007bff", "white")
        icon.save(filepath, "PNG")
        print(f"  ✅ {filename} ({size}x{size})")
    
    # Générer les icônes spéciales
    print("\n🎯 Génération des icônes spéciales...")
    for name, size in special_icons.items():
        filename = f"{name}.png"
        filepath = os.path.join(icons_dir, filename)
        
        # Utiliser la couleur spécifique
        color = special_colors.get(name, "#007bff")
        
        # Créer l'icône
        icon = create_icon(size, "TA", color, "white")
        icon.save(filepath, "PNG")
        print(f"  ✅ {filename} ({size}x{size}) - {color}")
    
    # Générer les icônes maskables
    print("\n🔄 Génération des icônes maskables...")
    maskable_sizes = [192, 512]  # Tailles principales pour maskable
    for size in maskable_sizes:
        filename = f"icon-{size}x{size}-maskable.png"
        filepath = os.path.join(icons_dir, filename)
        
        # Créer l'icône maskable
        icon = create_maskable_icon(size, "TA", "#007bff", "white")
        icon.save(filepath, "PNG")
        print(f"  ✅ {filename} ({size}x{size}) - Maskable")
    
    print(f"\n🎉 Génération terminée ! {len(icon_sizes) + len(special_icons) + len(maskable_sizes)} icônes créées dans {icons_dir}/")
    print("\n📋 Prochaines étapes:")
    print("  1. Vérifiez que toutes les icônes sont créées")
    print("  2. Testez votre PWA sur mobile")
    print("  3. Vérifiez l'installation dans Chrome DevTools > Application")
    print("  4. Testez les notifications push")

if __name__ == "__main__":
    main()
