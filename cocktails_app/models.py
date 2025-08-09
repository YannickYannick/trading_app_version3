from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from decimal import Decimal
from urllib.parse import quote


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Ingredient(models.Model):
    UNIT_CHOICES = [
        ("ml", "ml"),
        ("cl", "cl"),
        ("l", "l"),
        ("g", "g"),
        ("pcs", "pièces"),
    ]

    name = models.CharField(max_length=120, unique=True)
    default_unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="ml")
    description = models.TextField(blank=True)
    is_alcohol = models.BooleanField(default=False)
    buy_link = models.URLField(blank=True)

    def __str__(self) -> str:
        return self.name


class Cocktail(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="cocktails")
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    is_alcoholic = models.BooleanField(default=True)
    popularity = models.PositiveIntegerField(default=0)
    preparation_time_min = models.PositiveIntegerField(default=5)
    image = models.ImageField(upload_to="cocktails/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

    @property
    def image_url_or_placeholder(self) -> str:
        """Return a working image URL or a remote placeholder if missing/broken."""
        try:
            if self.image and getattr(self.image, "name", None) and self.image.storage.exists(self.image.name):
                return self.image.url
        except Exception:
            pass
        q = quote(self.name)
        # Use a deterministic placeholder to avoid hotlinking issues
        return f"https://placehold.co/640x480?text={q}"


class CocktailIngredient(models.Model):
    cocktail = models.ForeignKey(Cocktail, on_delete=models.CASCADE, related_name="recipe_items")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT, related_name="used_in")
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    unit = models.CharField(max_length=10, default="ml")
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("cocktail", "ingredient")

    def __str__(self) -> str:
        return f"{self.ingredient.name} - {self.quantity} {self.unit}"


class Promotion(models.Model):
    code = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=200, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="% de réduction")
    active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.code} ({self.percentage}%)"


class Order(models.Model):
    STATUS_CART = "cart"
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_CART, "Panier"),
        (STATUS_PENDING, "En attente"),
        (STATUS_PAID, "Payée"),
        (STATUS_CANCELLED, "Annulée"),
    ]

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="cocktails_orders")
    session_key = models.CharField(max_length=120, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CART)
    promotion = models.ForeignKey(Promotion, null=True, blank=True, on_delete=models.SET_NULL)
    customer_name = models.CharField(max_length=120, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=40, blank=True)
    delivery_address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def subtotal(self) -> Decimal:
        total = Decimal("0.00")
        for item in self.items.all():
            total += item.line_total
        return total

    @property
    def discount_amount(self) -> Decimal:
        if self.promotion and self.promotion.active:
            return (self.subtotal * self.promotion.percentage) / Decimal("100.0")
        return Decimal("0.00")

    @property
    def total(self) -> Decimal:
        return self.subtotal - self.discount_amount

    def __str__(self) -> str:
        return f"Commande #{self.id} - {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    cocktail = models.ForeignKey(Cocktail, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity

    def __str__(self) -> str:
        return f"{self.cocktail.name} x{self.quantity}"


class Formula(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    title = models.CharField(max_length=200)
    definition = models.TextField(blank=True)
    quantity_text = models.TextField(blank=True)
    cost_text = models.TextField(blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    cocktails = models.ManyToManyField(Cocktail, through="FormulaCocktail", related_name="formulas")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class FormulaCocktail(models.Model):
    formula = models.ForeignKey(Formula, on_delete=models.CASCADE, related_name="formula_items")
    cocktail = models.ForeignKey(Cocktail, on_delete=models.PROTECT)
    # How many servings of this cocktail are suggested within the formula
    servings = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("formula", "cocktail")

    def __str__(self) -> str:
        return f"{self.formula.name} → {self.cocktail.name} ({self.servings})"