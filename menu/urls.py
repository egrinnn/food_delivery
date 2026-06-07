# menu/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('', views.catalog, name='catalog'),
    path('menu/', views.catalog, name='catalog'),  # Дублируем для удобства
    path('delivery/', views.delivery_info, name='delivery_info'),
    
    # Аутентификация
    path('register/', views.register, name='register'),
    
    # Личный кабинет
    path('profile/', views.profile, name='profile'),
    path('profile/favorites/', views.favorites, name='favorites'),
    path('profile/favorites/toggle/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('profile/orders/', views.order_history, name='order_history'),
    
    # Корзина и заказы
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
]