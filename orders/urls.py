from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_order, name='create_order'),
    path('detail/<int:pk>/', views.order_detail, name='order_detail'),
    path('list/', views.order_list, name='order_list'),
    path('pay/<int:pk>/', views.pay_order, name='pay_order'),
    path('ship/<int:pk>/', views.ship_order, name='ship_order'),
]