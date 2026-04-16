from django.db import models


class Transaction(models.Model):
    ACCOUNT_CHOICES = [
        ('hyundai', '현대카드(용돈)'),
        ('shinhan', '신한카드(고정비)'),
        ('incident', '사건비통장'),
        ('cash_transfer', '현금/이체'),
    ]

    TYPE_CHOICES = [
        ('expense', '지출'),
        ('income', '환급/입금'),
        ('non_expense', '비지출(지원)'),
    ]

    DETAIL_CATEGORY_CHOICES = [
        ('외식', '외식'),
        ('커피', '커피'),
        ('주유', '주유'),
        ('쇼핑', '쇼핑'),
        ('병원', '병원'),
        ('고정비', '고정비'),
        ('생활', '생활'),
        ('기타', '기타'),
    ]

    date = models.DateField()
    description = models.CharField(max_length=100)
    amount = models.IntegerField()
    account_type = models.CharField(max_length=15, choices=ACCOUNT_CHOICES, default='hyundai')
    category = models.CharField(max_length=15, choices=TYPE_CHOICES, default='expense')
    detail_category = models.CharField(max_length=20, choices=DETAIL_CATEGORY_CHOICES, default='기타')

    is_fuel = models.BooleanField(default=False)
    price_per_liter = models.FloatField(null=True, blank=True)
    liters = models.FloatField(null=True, blank=True)

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