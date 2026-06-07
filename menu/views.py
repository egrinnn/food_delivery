# menu/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
import json
import logging
from .models import Product, Category, Order, OrderItem, Favorite, SavedAddress

logger = logging.getLogger(__name__)

def delivery_info(request):
    return render(request, 'delivery.html')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна!')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@require_GET
def catalog(request):
    categories = Category.objects.all()
    products = Product.objects.filter(is_available=True)
    cat_slug = request.GET.get('category')
    search = request.GET.get('search')
    
    if cat_slug:
        products = products.filter(category__slug=cat_slug)
    if search:
        products = products.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )
    
    return render(request, 'catalog.html', {
        'products': products, 
        'categories': categories,
        'current_category': cat_slug,
        'search_query': search
    })

@login_required
def profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        messages.success(request, 'Профиль обновлён!')
        return redirect('profile')
    return render(request, 'profile.html', {'user': request.user})

@login_required
@require_POST
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_available=True)
    fav, created = Favorite.objects.get_or_create(user=request.user, product=product)
    if not created:
        fav.delete()
    return JsonResponse({'is_favorite': created, 'product_id': product_id})

@login_required
def favorites(request):
    favs = Favorite.objects.filter(user=request.user).select_related('product')
    return render(request, 'favorites.html', {'favorites': favs})

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user)\
        .prefetch_related('items__product')\
        .order_by('-created_at')
    return render(request, 'order_history.html', {'orders': orders})

# === КОРЗИНА (на основе сессии) ===
def _get_cart(request):
    return request.session.get('cart', {})

def _save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True

def cart_view(request):
    cart = _get_cart(request)
    products = Product.objects.filter(id__in=cart.keys(), is_available=True)
    cart_items = []
    total = 0
    
    for p in products:
        qty = cart.get(str(p.id), 0)
        if qty > 0:
            subtotal = float(p.price) * qty
            total += subtotal
            cart_items.append({
                'product': p,
                'quantity': qty,
                'subtotal': subtotal
            })
    
    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total': total
    })

@require_POST
def add_to_cart(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id, is_available=True)
        cart = _get_cart(request)
        cart[str(product_id)] = cart.get(str(product_id), 0) + 1
        _save_cart(request, cart)
        return JsonResponse({'success': True, 'cart_count': sum(cart.values())})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_POST
def remove_from_cart(request, product_id):
    cart = _get_cart(request)
    if str(product_id) in cart:
        del cart[str(product_id)]
        _save_cart(request, cart)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'cart_count': sum(cart.values())})
    return redirect('cart')

@login_required
def checkout(request):
    if request.method == 'GET':
        saved_addresses = SavedAddress.objects.filter(user=request.user)
        return render(request, 'checkout.html', {'saved_addresses': saved_addresses})
    
    try:
        data = json.loads(request.body)
        cart = data.get('cart', [])
        order_type = data.get('order_type', 'delivery')
        
        if not cart:
            return JsonResponse({'success': False, 'error': 'Корзина пуста'}, status=400)
        
        # Валидация
        required = ['full_name', 'phone', 'email']
        if order_type == 'delivery':
            required.append('address')
        for field in required:
            if not data.get(field):
                return JsonResponse({'success': False, 'error': f'Заполните поле: {field}'}, status=400)
        
        # Подсчёт суммы
        subtotal = 0
        order_items_data = []
        for item in cart:
            product = Product.objects.filter(id=item['id'], is_available=True).first()
            if not product:
                return JsonResponse({'success': False, 'error': f'Товар "{item.get("name")}" недоступен'}, status=400)
            qty = int(item.get('qty', 1))
            price = float(product.price)
            subtotal += price * qty
            order_items_data.append({'product': product, 'quantity': qty, 'price': price})
        
        # Финальная цена с учётом типа заказа
        delivery_fee = 0
        discount = 0
        if order_type == 'delivery':
            delivery_fee = 0 if subtotal >= 1000 else 300
        else:
            discount = round(subtotal * 0.05, 2)
        
        total = subtotal + delivery_fee - discount
        
        # Создание заказа
        order = Order.objects.create(
            user=request.user,
            total_price=total,
            status='new',
            order_type=order_type,
            delivery_address=data['address'],
            customer_name=data['full_name'],
            customer_phone=data['phone'],
            customer_email=data['email'],
            delivery_time_type=data.get('delivery_time', 'asap'),
            scheduled_delivery=data.get('scheduled_time') if data.get('delivery_time') == 'scheduled' else None
        )
        
        for item_data in order_items_data:
            OrderItem.objects.create(
                order=order, product=item_data['product'],
                quantity=item_data['quantity'], price_at_time=item_data['price']
            )
        
        # 💾 Сохраняем ВСЕ данные доставки для будущих заказов
        if data.get('save_address'):
            SavedAddress.objects.get_or_create(
                user=request.user,
                order_type=order_type,
                address=data['address'] if order_type == 'delivery' else '',
                phone=data['phone'],
                defaults={
                    'label': 'Дом' if order_type == 'delivery' else 'Самовывоз',
                }
            )
        
        _save_cart(request, {})
        _notify_admins_new_order(order)
        
        return JsonResponse({'success': True, 'order_id': order.id})
        
    except json.JSONDecodeError as e:
        return JsonResponse({'success': False, 'error': f'Неверный формат данных: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f'Checkout error: {e}', exc_info=True)
        return JsonResponse({'success': False, 'error': 'Внутренняя ошибка сервера'}, status=500)
    

# === УВЕДОМЛЕНИЕ АДМИНОВ ===
def _notify_admins_new_order(order):
    """Отправляет уведомление администраторам о новом заказе"""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admins = User.objects.filter(is_superuser=True, is_active=True)
        
        if not admins:
            return
        
        subject = f"🆕 Новый заказ #{order.id} — {order.total_price:.0f} ₽"
        
        # Формируем текст уведомления
        items = '\n'.join([f"• {i.product.name} × {i.quantity} — {i.subtotal:.0f} ₽" for i in order.items.all()])
        delivery_time = order.get_delivery_time_display()
        
        message = f"""
Новый заказ #{order.id}

Клиент: {order.customer_name}
Телефон: {order.customer_phone}
Email: {order.customer_email}
Адрес: {order.delivery_address}
Время доставки: {delivery_time}

Товары:
{items}

Итого: {order.total_price:.0f} ₽

Админ-панель: {settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost/admin'}/menu/order/{order.id}/change/
        """.strip()
        
        # Отправка (fail_silently=True чтобы не ломать заказ при ошибке почты)
        for admin in admins:
            if admin.email:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin.email],
                    fail_silently=True,
                )
        
        # Сообщение в админку
        messages.success(
            None,  # type: ignore
            f"🆕 Новый заказ #{order.id} на сумму {order.total_price:.0f} ₽ от {order.customer_name}",
            extra_tags='admin-notification'
        )
        
    except Exception as e:
        logger.error(f'Failed to notify admins: {e}')

def home(request):
    popular = Product.objects.filter(is_available=True).order_by('?')[:4]
    return render(request, 'home.html', {'popular_products': popular})