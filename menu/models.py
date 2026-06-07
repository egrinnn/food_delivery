# menu/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(blank=True, null=True, help_text="Ссылка на изображение")
    is_available = models.BooleanField(default=True, help_text="Показывать в меню")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
        verbose_name = "Блюдо"
        verbose_name_plural = "Блюда"


class SavedAddress(models.Model):
    TYPE_CHOICES = [
        ('delivery', '🚚 Доставка'),
        ('pickup', '🏪 Самовывоз'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_addresses')
    label = models.CharField(max_length=50, blank=True, help_text="Метка: Дом, Работа, Самовывоз")
    order_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='delivery')
    address = models.TextField(blank=True, help_text="Адрес доставки (пусто для самовывоза)")
    phone = models.CharField(max_length=20, blank=True, help_text="Телефон для этого способа")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        if self.order_type == 'pickup':
            return f"🏪 Самовывоз — {self.user.username}"
        return f"{self.label or 'Адрес'} — {self.user.username}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Сохранённый способ получения"
        verbose_name_plural = "Сохранённые способы получения"


class Order(models.Model):
    STATUS_CHOICES = [
        ('new', '🆕 Новый'),
        ('confirmed', '✅ Подтверждён'),
        ('preparing', '👨‍🍳 Готовится'),
        ('delivering', '🚚 Доставляется'),
        ('delivered', '✨ Доставлен'),
        ('cancelled', '❌ Отменён'),
    ]
    
    DELIVERY_TIME_CHOICES = [
        ('asap', 'Как можно скорее'),
        ('scheduled', 'По расписанию'),
    ]

    ORDER_TYPE_CHOICES = [
        ('delivery', 'Доставка'),
        ('pickup', 'Самовывоз'),
    ]
    
    # Связь с пользователем
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    
    # Данные заказа
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    
    order_type = models.CharField(
        max_length=10, 
        choices=ORDER_TYPE_CHOICES, 
        default='delivery',
        help_text="Доставка или самовывоз"
    )
    
    # Адрес доставки 
    delivery_address = models.TextField(help_text="Адрес доставки")
    
    #  Данные получателя
    customer_name = models.CharField(max_length=200, blank=True, help_text="ФИО получателя")
    customer_phone = models.CharField(max_length=20, blank=True, help_text="Телефон получателя")
    customer_email = models.EmailField(blank=True, help_text="Email для уведомлений")
    
    #  Время доставки
    delivery_time_type = models.CharField(
        max_length=20, 
        choices=DELIVERY_TIME_CHOICES, 
        default='asap',
        help_text="Тип доставки"
    )
    scheduled_delivery = models.DateTimeField(
        null=True, blank=True, 
        help_text="Запланированное время (если выбрано 'По расписанию')"
    )
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        name = self.customer_name or self.user.get_full_name() or self.user.username
        return f"Заказ #{self.id} — {name}"
    
    def get_delivery_info_display(self):
        """Читаемое отображение способа и времени получения"""
        if self.order_type == 'pickup':
            return "🏪 Самовывоз"
        if self.delivery_time_type == 'asap':
            return "🚚 Как можно скорее (30–45 мин)"
        elif self.scheduled_delivery:
            return f"📅 {self.scheduled_delivery.strftime('%d.%m.%Y %H:%M')}"
        return "Не указано"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2, help_text="Цена на момент заказа")
    
    @property
    def subtotal(self):
        """Сумма по позиции"""
        return self.quantity * self.price_at_time
    
    def __str__(self):
        return f"{self.product.name} × {self.quantity}"
    
    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} ❤️ {self.product.name}"
    
    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"