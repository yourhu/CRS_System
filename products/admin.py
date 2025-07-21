from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Category, Product
from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    list_filter = ['parent']
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'merchant', 'price', 'stock', 'created_at']
    list_filter = ['category', 'merchant', 'created_at']
    search_fields = ['name', 'description']
    list_per_page = 20