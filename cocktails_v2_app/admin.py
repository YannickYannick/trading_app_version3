from django.contrib import admin
from .models import (
    Tag, Category, InventoryItem, Product, ProductVariant,
    OptionGroup, Option, RecipeItem, HappyHour, Order, OrderItem
)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


class OptionInline(admin.TabularInline):
    model = Option
    extra = 1


class OptionGroupInline(admin.StackedInline):
    model = OptionGroup
    extra = 0


class RecipeItemInline(admin.TabularInline):
    model = RecipeItem
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "base_price", "is_alcoholic", "is_active")
    list_filter = ("category", "is_alcoholic", "is_active", "tags")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductVariantInline, RecipeItemInline, OptionGroupInline]


admin.site.register(Tag)
admin.site.register(Category)
admin.site.register(InventoryItem)
admin.site.register(ProductVariant)
admin.site.register(OptionGroup)
admin.site.register(Option)
admin.site.register(RecipeItem)
admin.site.register(HappyHour)
admin.site.register(Order)
admin.site.register(OrderItem)