from django import template

register = template.Library()

@register.filter
def dict_key(d, key):
    """Filtre pour accéder à une clé de dictionnaire dans un template Django"""
    try:
        return d.get(key)
    except Exception:
        return None 