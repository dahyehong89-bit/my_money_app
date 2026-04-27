from django.db import models
from .category_config import ACCOUNT_CHOICES, TYPE_CHOICES, DETAIL_CATEGORY_CHOICES


class Transaction(models.Model):
    date = models.DateField()
    description = models.CharField(max_length=100)
    amount = models.IntegerField()
    account_type = models.CharField(max_length=15, choices=ACCOUNT_CHOICES, default='hyundai')
    category = models.CharField(max_length=15, choices=TYPE_CHOICES, default='expense')
    detail_category = models.CharField(max_length=20, choices=DETAIL_CATEGORY_CHOICES, default='기타')

    is_fuel = models.BooleanField(default=False)
    price_per_liter = models.FloatField(null=True, blank=True)
    liters = models.FloatField(null=True, blank=True)
    odometer = models.PositiveIntegerField(null=True, blank=True)  # 누적 주행거리(km)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.is_fuel and self.price_per_liter and self.amount:
            self.liters = round(self.amount / self.price_per_liter, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date} - {self.description} ({self.amount}원)"

class CheckList(models.Model):
    month = models.DateField()
    content = models.CharField(max_length=100)
    amount = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.month.strftime('%Y-%m')} - {self.content}"
    

class Memo(models.Model):
    text = models.CharField(max_length=255)
    checked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    checked_at = models.DateTimeField(null=True, blank=True)  # 체크한 시각