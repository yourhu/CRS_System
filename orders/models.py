from django.db import models
from django.contrib.auth.models import User

from CRS_System import settings
from products.models import Product

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='总价', default=0.00)
    status = models.CharField(
        max_length=20,
        choices=[('pending', '待支付'), ('paid', '已支付'), ('shipped', '已发货'), ('completed', '已完成'), ('cancelled', '已取消')],
        default='pending',
        verbose_name='状态'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return f"订单 {self.id} - {self.user.username}"

    class Meta:
        db_table = 'orders_order'
        verbose_name = '订单信息'
        verbose_name_plural = '订单信息'

class OrderItem(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='items', verbose_name='订单')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, verbose_name='产品')
    quantity = models.PositiveIntegerField(verbose_name='数量', default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='单价')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    class Meta:
        db_table = 'orders_orderitem'
        verbose_name = '订单项信息'
        verbose_name_plural = '订单项信息'

    def get_total(self):
        return self.quantity * self.price