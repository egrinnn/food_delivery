
from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Category, Product, Order, OrderItem, Favorite, SavedAddress


# Inline для позиций заказа
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price_at_time', 'subtotal')
    can_delete = False

    def subtotal(self, obj):
        return f"{obj.subtotal:.0f} ₽"
    subtotal.short_description = 'Сумма'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name', 'description')
    list_editable = ('price', 'is_available')
    ordering = ('category', 'name')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_type_badge', 'customer_info', 'total_display', 'status_badge', 'delivery_info', 'created_at', 'new_indicator')
    list_filter = ('status', 'order_type', 'delivery_time_type', 'created_at')
    
    search_fields = ('id', 'customer_name', 'customer_phone', 'delivery_address', 'user__username', 'user__email')
    
    readonly_fields = ('created_at', 'updated_at', 'total_price')
    inlines = [OrderItemInline]
    actions = ['mark_confirmed', 'mark_preparing', 'mark_delivering', 'mark_delivered', 'mark_cancelled']

    def order_type_badge(self, obj):
        if obj.order_type == 'pickup':
            return format_html('<span style="background:#c9a97a;color:#fff;padding:4px 10px;border-radius:12px;font-size:0.8em">🏪 Самовывоз</span>')
        return format_html('<span style="background:#7a9a7a;color:#fff;padding:4px 10px;border-radius:12px;font-size:0.8em">🚚 Доставка</span>')
    order_type_badge.short_description = 'Тип'
    
    # Показываем уведомление при входе в раздел заказов
    def changelist_view(self, request, extra_context=None):
        new_count = Order.objects.filter(status='new').exclude(id__in=request.session.get('seen_orders', [])).count()
        if new_count > 0:
            seen = request.session.get('seen_orders', [])
            new_ids = list(Order.objects.filter(status='new').values_list('id', flat=True))
            request.session['seen_orders'] = list(set(seen + new_ids))
            request.session.modified = True
            
            self.message_user(
                request,
                f"🆕 <b>{new_count} новых заказов</b> ожидают обработки!",
                level=messages.WARNING,
                extra_tags='safe'
            )
        return super().changelist_view(request, extra_context)

    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'user', 'order_type', 'status', 'total_price', 'created_at', 'updated_at')
        }),
        ('Данные получателя', {
            'fields': ('customer_name', 'customer_phone', 'customer_email')
        }),
        ('Доставка / Получение', {
            'fields': ('delivery_address', 'delivery_time_type', 'scheduled_delivery')
        }),
    )

    def customer_info(self, obj):
        name = obj.customer_name or obj.user.get_full_name() or obj.user.username
        phone = obj.customer_phone or '—'
        return format_html(f'{name}<br><small style="color:#6c757d">{phone}</small>')
    customer_info.short_description = 'Клиент'

    def total_display(self, obj):
        return f"{obj.total_price:.0f} ₽"
    total_display.short_description = 'Сумма'

    def status_badge(self, obj):
        colors = {
            'new': '#ffc107', 'confirmed': '#17a2b8',
            'preparing': '#0d6efd', 'delivering': '#6f42c1',
            'delivered': '#198754', 'cancelled': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        label = dict(Order.STATUS_CHOICES).get(obj.status, obj.status)
        return format_html(
            f'<span style="background:{color};color:#fff;padding:4px 10px;'
            f'border-radius:12px;font-size:0.8em;font-weight:500">{label}</span>'
        )
    status_badge.short_description = 'Статус'

    def delivery_info(self, obj):
        if obj.order_type == 'pickup':
            return format_html('🏪 <b>Самовывоз</b><br><small style="color:#6c757d">Тверская, 1</small>')
        
        time = obj.get_delivery_time_display()
        addr = (obj.delivery_address[:30] + '…') if len(obj.delivery_address) > 30 else obj.delivery_address
        return format_html(f'{time}<br><small style="color:#6c757d">{addr}</small>')
    delivery_info.short_description = 'Получение'
    
    # Индикатор нового заказа в списке
    def new_indicator(self, obj):
        if obj.status == 'new':
            return mark_safe('<span style="color:#dc3545;font-weight:bold">🆕</span>')
        return '✓'
    new_indicator.short_description = ''
    new_indicator.admin_order_field = 'created_at'

    # === Массовые действия ===
    def _update_status(self, request, queryset, status, message):
        count = queryset.update(status=status)
        seen = request.session.get('seen_orders', [])
        updated_ids = list(queryset.values_list('id', flat=True))
        request.session['seen_orders'] = [i for i in seen if i not in updated_ids]
        request.session.modified = True
        
        self.message_user(request, f"{message} ({count} заказов)")

    @admin.action(description="✅ Подтвердить выбранные")
    def mark_confirmed(self, request, queryset):
        self._update_status(request, queryset, 'confirmed', "✅ Статус изменён на 'Подтверждён'")

    @admin.action(description="👨‍🍳 Готовится")
    def mark_preparing(self, request, queryset):
        self._update_status(request, queryset, 'preparing', "👨‍🍳 Статус изменён на 'Готовится'")

    @admin.action(description="🚚 Доставляется")
    def mark_delivering(self, request, queryset):
        self._update_status(request, queryset, 'delivering', "🚚 Статус изменён на 'Доставляется'")

    @admin.action(description="✨ Доставлен")
    def mark_delivered(self, request, queryset):
        self._update_status(request, queryset, 'delivered', "✨ Статус изменён на 'Доставлен'")

    @admin.action(description="❌ Отменить выбранные")
    def mark_cancelled(self, request, queryset):
        self._update_status(request, queryset, 'cancelled', "❌ Статус изменён на 'Отменён'")


@admin.register(SavedAddress)
class SavedAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'order_type', 'label', 'address_preview', 'phone', 'created_at')
    list_filter = ('order_type', 'created_at')
    search_fields = ('user__username', 'address', 'phone', 'label')
    readonly_fields = ('created_at',)

    def address_preview(self, obj):
        if obj.order_type == 'pickup':
            return '🏪 Самовывоз (Тверская, 1)'
        return (obj.address[:40] + '…') if len(obj.address) > 40 else obj.address
    address_preview.short_description = 'Адрес / Способ'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('user',)
    search_fields = ('user__username', 'product__name')


# Глобальное уведомление при входе в админку
def admin_site_override(original_index):
    def wrapper(self, request, extra_context=None):
        new_count = Order.objects.filter(status='new').count()
        if new_count > 0:
            messages.warning(
                request,
                f"🆕 <b>{new_count} новых заказов</b> в разделе <a href='/admin/menu/order/'>Заказы</a>!",
                extra_tags='safe'
            )
        return original_index(self, request, extra_context)
    return wrapper

if hasattr(admin.AdminSite, 'index'):
    admin.AdminSite.index = admin_site_override(admin.AdminSite.index)