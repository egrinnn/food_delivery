document.addEventListener('DOMContentLoaded', () => {
    console.log('main.js loaded');
    const cartCount = document.getElementById('cart-count');
    if (cartCount) {
        try {
            const cart = JSON.parse(localStorage.getItem('cart')) || [];
            const totalCount = cart.reduce((sum, i) => sum + (parseInt(i.qty) || 0), 0);
            cartCount.textContent = totalCount;
        } catch (e) {
            console.error('Ошибка чтения корзины:', e);
            cartCount.textContent = '0';
        }
    }

    // ================= ТЕМА =================
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const html = document.documentElement;

    if (themeToggle && themeIcon) {
        // Загружаем сохранённую тему
        const savedTheme = localStorage.getItem('theme') || 'light';
        html.setAttribute('data-bs-theme', savedTheme);
        updateThemeIcon(savedTheme);

        // Обработчик клика
        themeToggle.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const currentTheme = html.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';

            html.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);

            // Визуальный фидбек
            themeToggle.blur();
        });
    }

    function updateThemeIcon(theme) {
        const icon = document.getElementById('themeIcon');
        if (icon) {
            icon.className = theme === 'light' ? 'bi bi-moon-stars' : 'bi bi-sun-fill';
        }
    }

    // ================= КОРЗИНА: ДОБАВЛЕНИЕ =================
    document.querySelectorAll('.add-to-cart').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const productId = btn.dataset.id;
            // Получаем токен из скрытой формы
            const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

            if (!csrf) {
                console.warn('⚠️ CSRF token not found');
                return;
            }

            try {
                const res = await fetch(`/cart/add/${productId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrf,
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'application/json'
                    }
                });

                if (!res.ok) {
                    const errorText = await res.text();
                    console.error(`Server ${res.status}:`, errorText.substring(0, 300));
                    alert(`Ошибка сервера: ${res.status}. Проверьте консоль (F12).`);
                    return;
                }

                const data = await res.json();

                if (data.success) {
                    const productCard = btn.closest('.card');
                    const productImage = productCard?.querySelector('.card-img-top')?.src;

                    let cart = JSON.parse(localStorage.getItem('cart')) || [];
                    const existing = cart.find(i => i.id == productId);

                    if (existing) existing.qty++;
                    else cart.push({ id: productId, name: btn.dataset.name, price: parseFloat(btn.dataset.price), qty: 1, image: productImage || null });

                    localStorage.setItem('cart', JSON.stringify(cart));

                    const cartCount = document.getElementById('cart-count');
                    if (cartCount) {
                        cartCount.textContent = cart.reduce((sum, i) => sum + (parseInt(i.qty) || 0), 0);
                    }
                    const originalHTML = btn.innerHTML;
                    btn.innerHTML = '<i class="bi bi-check-lg me-2"></i>Добавлено';
                    btn.disabled = true;
                    setTimeout(() => { btn.innerHTML = originalHTML; btn.disabled = false; }, 1500);
                } else {
                    alert('Ошибка: ' + (data.error || 'Не удалось добавить товар'));
                }
            } catch (err) {
                console.error('Cart error:', err);
                alert('Ошибка сети или парсинга ответа');
            }
        });
    });

    // ================= ИЗБРАННОЕ =================
    document.querySelectorAll('.fav-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const productId = btn.dataset.id;
            const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
            if (!csrf) return;

            try {
                const res = await fetch(`/profile/favorites/toggle/${productId}/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest' }
                });
                const data = await res.json();
                const icon = btn.querySelector('i');
                if (icon) {
                    icon.className = data.is_favorite ? 'bi bi-heart-fill' : 'bi bi-heart';
                    btn.classList.toggle('active', data.is_favorite);
                }
            } catch (err) {
                console.error('❌ Favorites error:', err);
            }
        });
    });

    // ================= ПОВТОР ЗАКАЗА =================
    document.querySelectorAll('.repeat-order-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const card = btn.closest('.order-card');
            const items = card?.querySelectorAll('.order-item') || [];
            let cart = JSON.parse(localStorage.getItem('cart')) || [];

            items.forEach(item => {
                const id = item.dataset.id;
                const qty = parseInt(item.dataset.qty);
                const price = parseFloat(item.dataset.price);
                const name = item.dataset.name;

                const existing = cart.find(i => i.id == id);
                if (existing) {
                    existing.qty += qty;
                } else {
                    cart.push({ id, name, price, qty });
                }
            });

            localStorage.setItem('cart', JSON.stringify(cart));
            window.location.href = '/cart/';
        });
    });
});
