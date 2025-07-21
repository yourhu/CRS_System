from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=[('customer', '客户'), ('merchant', '商家'), ('admin', '管理员')],
        default='customer',
        verbose_name='身份'
    )

    class Meta:
        db_table = 'user'
        verbose_name = '用户表'
        verbose_name_plural = verbose_name