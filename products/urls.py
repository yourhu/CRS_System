from django.urls import path
from . import views

urlpatterns = [
    path('category/<int:pk>/', views.category_detail, name='category_detail'),
    path('merchant/dashboard/', views.merchant_dashboard, name='merchant_dashboard'),
    path('create/', views.create_product.as_view(), name='create_product'),
    path('merchant/product/<int:pk>/edit/', views.edit_product, name='edit_product'),
    path('merchant/product/<int:pk>/delete/', views.delete_product, name='delete_product'),
    path('merchant/orders/', views.merchant_orders, name='merchant_orders'),  # 添加订单管理路径
    path('detail/<int:pk>/', views.product_detail, name='product_detail'),
    path('sales_statistics/', views.sales_statistics, name='sales_statistics'),
    path('search/', views.search_products, name='search_products'),
]