from django.contrib import admin
from .models import (
    Category,
    Ingredient,
    Cocktail,
    CocktailIngredient,
    Order,
    OrderItem,
    Promotion,
    Formula,
    FormulaCocktail,
)


class CocktailIngredientInline(admin.TabularInline):
    model = CocktailIngredient
    extra = 1


@admin.register(Cocktail)
class CocktailAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_alcoholic", "is_active")
    list_filter = ("category", "is_alcoholic", "is_active")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [CocktailIngredientInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "default_unit", "is_alcohol")
    list_filter = ("is_alcohol",)
    search_fields = ("name",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "created_at", "total")
    list_filter = ("status", "created_at")
    readonly_fields = ("created_at", "updated_at")
    inlines = [OrderItemInline]


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("code", "percentage", "active", "valid_until")
    list_filter = ("active",)
    search_fields = ("code",)


class FormulaCocktailInline(admin.TabularInline):
    model = FormulaCocktail
    extra = 1


@admin.register(Formula)
class FormulaAdmin(admin.ModelAdmin):
    list_display = ("name", "title", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "title")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [FormulaCocktailInline]