from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from decimal import Decimal


class Tag(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class InventoryItem(models.Model):
    UNIT_CHOICES = [("ml", "ml"), ("cl", "cl"), ("l", "l"), ("g", "g"), ("pcs", "pièces")]
    name = models.CharField(max_length=120, unique=True)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="ml")
    current_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0"))
    reorder_threshold = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0"))
    is_alcohol = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="products")
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    is_alcoholic = models.BooleanField(default=True)
    image = models.ImageField(upload_to="cocktails_v2/", null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class ProductVariant(models.Model):
    SIZE_CHOICES = [("S", "Small"), ("M", "Medium"), ("L", "Large")]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=80)
    size = models.CharField(max_length=2, choices=SIZE_CHOICES, default="M")
    price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        unique_together = ("product", "name")

    def __str__(self) -> str:
        return f"{self.product.name} - {self.name}"


class OptionGroup(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="option_groups")
    name = models.CharField(max_length=80)
    required = models.BooleanField(default=False)
    max_choices = models.PositiveIntegerField(default=1)

    def __str__(self) -> str:
        return f"{self.product.name} - {self.name}"


class Option(models.Model):
    group = models.ForeignKey(OptionGroup, on_delete=models.CASCADE, related_name="options")
    name = models.CharField(max_length=80)
    price_delta = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))

    def __str__(self) -> str:
        return f"{self.group.name} - {self.name}"


class RecipeItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="recipe")
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.CharField(max_length=10, default="ml")
    note = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = ("product", "inventory_item")


class HappyHour(models.Model):
    name = models.CharField(max_length=100)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    weekday = models.PositiveSmallIntegerField(help_text="0=Lundi … 6=Dimanche")
    start_time = models.TimeField()
    end_time = models.TimeField()
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.discount_percent}%)"


class Order(models.Model):
    STATUS_CHOICES = [
        ("cart", "Panier"),
        ("preparing", "Préparation"),
        ("ready", "Prête"),
        ("paid", "Payée"),
        ("cancelled", "Annulée"),
    ]

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="cocktails_v2_orders")
    session_key = models.CharField(max_length=120, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="cart")
    table_number = models.CharField(max_length=10, blank=True)
    customer_name = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def subtotal(self) -> Decimal:
        total = Decimal("0.00")
        for item in self.items.all():
            total += item.line_total
        return total

    @property
    def total(self) -> Decimal:
        return self.subtotal


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    selected_options = models.ManyToManyField(Option, blank=True)

    @property
    def line_total(self) -> Decimal:
        options_total = sum((opt.price_delta for opt in self.selected_options.all()), Decimal("0.00"))
        base = self.unit_price + options_total
        return base * self.quantity