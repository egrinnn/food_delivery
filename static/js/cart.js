let cart = JSON.parse(localStorage.getItem('cart')) || [];

function updateCartUI() {
    document.querySelectorAll('.cart-count').forEach(el => el.textContent = cart.length);
}

function addToCart(id, name, price) {
    const existing = cart.find(item => item.id == id);
    if(existing) existing.qty++;
    else cart.push({ id, name, price, qty: 1 });
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartUI();
    alert(`${name} добавлен в корзину`);
}

function getCart() { return cart; }
function clearCart() { cart = []; localStorage.removeItem('cart'); updateCartUI(); }

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.add-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.id;
            addToCart(id, btn.dataset.name, parseFloat(btn.dataset.price));
        });
    });
    updateCartUI();
});