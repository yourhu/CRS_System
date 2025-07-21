from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='分类名称')
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name='父级分类'
    )

    class Meta:
        db_table = 'category'
        verbose_name = '商品分类'
        verbose_name_plural = '商品分类'

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name='商品名称')
    description = models.TextField(verbose_name='商品描述')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='商品价格'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        verbose_name='所属分类'
    )
    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='商家'
    )
    stock = models.IntegerField(verbose_name='库存数量')
    specifications = models.JSONField(verbose_name='商品规格')
    image = models.ImageField(
        upload_to='products/images/',
        null=True,
        blank=True,
        verbose_name='商品图片'
    )  # 新增图片字段
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )

    class Meta:
        db_table = 'product'
        verbose_name = '商品信息'
        verbose_name_plural = '商品信息'

    def __str__(self):
        return self.name