/* ==========================================================================
   Flower Shop - Customer Web App (Telegram Mini App)
   ========================================================================== */

(function () {
    'use strict';

    // -------------------------------------------------------------------------
    // Telegram WebApp initialization
    // -------------------------------------------------------------------------
    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg) {
        tg.ready();
        tg.expand();
    }

    // -------------------------------------------------------------------------
    // Constants
    // -------------------------------------------------------------------------
    const API_BASE = '/api';

    // -------------------------------------------------------------------------
    // Application state
    // -------------------------------------------------------------------------
    const state = {
        products: [],
        categories: [],
        stores: [],
        cart: null,          // { id, user_id, items: [...] }
        currentView: 'catalog',
        previousView: null,
        selectedCategory: null,
        selectedProduct: null,
        deliveryType: 'pickup',
        selectedStoreId: null,
        pickupTime: '',
        deliveryAddress: '',
        isLoading: false,
    };

    // -------------------------------------------------------------------------
    // DOM references
    // -------------------------------------------------------------------------
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const dom = {
        navTabs: $('#navTabs'),
        content: $('#content'),
        cartBadge: $('#cartBadge'),
        headerCartBtn: $('#headerCartBtn'),
        // Views
        catalogView: $('#catalogView'),
        productDetailView: $('#productDetailView'),
        cartView: $('#cartView'),
        checkoutView: $('#checkoutView'),
        // Catalog
        categoryChips: $('#categoryChips'),
        productsGrid: $('#productsGrid'),
        catalogLoading: $('#catalogLoading'),
        catalogEmpty: $('#catalogEmpty'),
        // Product detail
        productDetail: $('#productDetail'),
        productLoading: $('#productLoading'),
        // Cart
        cartContent: $('#cartContent'),
        cartLoading: $('#cartLoading'),
        cartEmpty: $('#cartEmpty'),
        // Checkout
        checkoutContent: $('#checkoutContent'),
        // Toast
        toastContainer: $('#toastContainer'),
        // Error
        errorOverlay: $('#errorOverlay'),
        errorMessage: $('#errorMessage'),
        errorRetryBtn: $('#errorRetryBtn'),
        // Misc
        goToCatalogBtn: $('#goToCatalogBtn'),
    };

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    /** Get the Telegram user id (or a fallback for testing) */
    function getUserId() {
        if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
            return tg.initDataUnsafe.user.id;
        }
        // Fallback for local dev/testing
        return 0;
    }

    /** Format a price in rubles */
    function formatPrice(price) {
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(price);
    }

    /** Escape HTML to prevent XSS */
    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /** Show a toast notification */
    function showToast(message, type) {
        type = type || 'info';
        var toast = document.createElement('div');
        toast.className = 'toast ' + type;
        toast.textContent = message;
        dom.toastContainer.appendChild(toast);
        setTimeout(function () {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 2600);
    }

    /** Show global error overlay */
    function showError(message, retryFn) {
        dom.errorMessage.textContent = message || 'Произошла ошибка. Попробуйте ещё раз.';
        dom.errorOverlay.style.display = 'flex';
        dom.errorRetryBtn.onclick = function () {
            dom.errorOverlay.style.display = 'none';
            if (typeof retryFn === 'function') retryFn();
        };
    }

    /** Generic fetch wrapper with error handling */
    async function apiFetch(path, options) {
        options = options || {};
        var url = API_BASE + path;
        var defaults = {
            headers: { 'Content-Type': 'application/json' },
        };
        var config = Object.assign({}, defaults, options);
        if (options.body && typeof options.body === 'object') {
            config.body = JSON.stringify(options.body);
        }

        var response = await fetch(url, config);
        if (!response.ok) {
            var errorText = '';
            try {
                var errorData = await response.json();
                errorText = errorData.detail || errorData.message || response.statusText;
            } catch (_e) {
                errorText = response.statusText;
            }
            throw new Error(errorText);
        }

        // Handle 204 No Content
        if (response.status === 204) return null;

        return response.json();
    }

    // -------------------------------------------------------------------------
    // Navigation
    // -------------------------------------------------------------------------

    function navigateTo(viewName) {
        state.previousView = state.currentView;
        state.currentView = viewName;

        // Hide all views
        var views = $$('.view');
        for (var i = 0; i < views.length; i++) {
            views[i].style.display = 'none';
        }

        // Update nav tabs
        var tabs = $$('.nav-tab');
        for (var i = 0; i < tabs.length; i++) {
            tabs[i].classList.toggle('active', tabs[i].dataset.view === viewName);
        }

        // Show active view
        switch (viewName) {
            case 'catalog':
                dom.catalogView.style.display = 'block';
                hideBackButton();
                break;
            case 'productDetail':
                dom.productDetailView.style.display = 'block';
                showBackButton();
                break;
            case 'cart':
                dom.cartView.style.display = 'block';
                hideBackButton();
                loadCart();
                break;
            case 'checkout':
                dom.checkoutView.style.display = 'block';
                showBackButton();
                renderCheckout();
                break;
        }

        // Hide MainButton when navigating (it will be shown if needed)
        hideMainButton();

        // Scroll to top
        window.scrollTo(0, 0);
    }

    function goBack() {
        if (state.currentView === 'productDetail') {
            navigateTo('catalog');
        } else if (state.currentView === 'checkout') {
            navigateTo('cart');
        } else {
            navigateTo('catalog');
        }
    }

    // Telegram BackButton
    function showBackButton() {
        if (tg && tg.BackButton) {
            tg.BackButton.show();
        }
    }

    function hideBackButton() {
        if (tg && tg.BackButton) {
            tg.BackButton.hide();
        }
    }

    // Telegram MainButton
    function showMainButton(text, callback) {
        if (tg && tg.MainButton) {
            tg.MainButton.setText(text);
            tg.MainButton.show();
            tg.MainButton.onClick(callback);
        }
    }

    function hideMainButton() {
        if (tg && tg.MainButton) {
            tg.MainButton.hide();
            tg.MainButton.offClick();
        }
    }

    function setMainButtonLoading(isLoading) {
        if (tg && tg.MainButton) {
            if (isLoading) {
                tg.MainButton.showProgress();
                tg.MainButton.disable();
            } else {
                tg.MainButton.hideProgress();
                tg.MainButton.enable();
            }
        }
    }

    // -------------------------------------------------------------------------
    // Catalog
    // -------------------------------------------------------------------------

    async function loadCategories() {
        try {
            var data = await apiFetch('/catalog/categories/');
            state.categories = data || [];
        } catch (err) {
            console.error('Failed to load categories:', err);
            state.categories = [];
        }
        renderCategoryChips();
    }

    async function loadProducts(categoryId) {
        dom.catalogLoading.style.display = 'flex';
        dom.productsGrid.innerHTML = '';
        dom.catalogEmpty.style.display = 'none';

        try {
            var path = '/catalog/products/';
            if (categoryId) {
                path += '?category_id=' + categoryId;
            }
            var data = await apiFetch(path);
            state.products = data || [];
        } catch (err) {
            console.error('Failed to load products:', err);
            state.products = [];
            showToast('Не удалось загрузить товары', 'error');
        }

        dom.catalogLoading.style.display = 'none';
        renderProductsGrid();
    }

    async function viewProduct(productId) {
        navigateTo('productDetail');
        dom.productLoading.style.display = 'flex';
        dom.productDetail.innerHTML = '';

        try {
            var product = await apiFetch('/catalog/products/' + productId + '/');
            state.selectedProduct = product;

            // Track view event (analytics) - fire and forget
            trackProductView(productId);

            renderProductDetail(product);
        } catch (err) {
            console.error('Failed to load product:', err);
            showToast('Не удалось загрузить товар', 'error');
            navigateTo('catalog');
        }

        dom.productLoading.style.display = 'none';
    }

    function trackProductView(productId) {
        apiFetch('/analytics/events/', {
            method: 'POST',
            body: {
                event_type: 'product_view',
                user_id: getUserId(),
                product_id: productId,
            },
        }).catch(function () { /* ignore analytics errors */ });
    }

    function renderCategoryChips() {
        var html = '<button class="category-chip active" data-category="">Все</button>';
        for (var i = 0; i < state.categories.length; i++) {
            var cat = state.categories[i];
            html += '<button class="category-chip" data-category="' + cat.id + '">'
                + escapeHtml(cat.name) + '</button>';
        }
        dom.categoryChips.innerHTML = html;

        // Attach click handlers
        var chips = dom.categoryChips.querySelectorAll('.category-chip');
        for (var i = 0; i < chips.length; i++) {
            chips[i].addEventListener('click', onCategoryClick);
        }
    }

    function onCategoryClick(e) {
        var categoryId = e.currentTarget.dataset.category;
        state.selectedCategory = categoryId || null;

        // Update active chip
        var chips = dom.categoryChips.querySelectorAll('.category-chip');
        for (var i = 0; i < chips.length; i++) {
            chips[i].classList.toggle('active', chips[i].dataset.category === categoryId);
        }

        loadProducts(state.selectedCategory);
    }

    function renderProductsGrid() {
        if (state.products.length === 0) {
            dom.productsGrid.innerHTML = '';
            dom.catalogEmpty.style.display = 'flex';
            return;
        }

        dom.catalogEmpty.style.display = 'none';
        var html = '';

        for (var i = 0; i < state.products.length; i++) {
            var p = state.products[i];
            var imageHtml = '';
            if (p.image_url) {
                imageHtml = '<img class="product-card-image" src="'
                    + escapeHtml(p.image_url) + '" alt="'
                    + escapeHtml(p.name)
                    + '" loading="lazy" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';">'
                    + '<div class="product-card-image-placeholder" style="display:none;">&#127803;</div>';
            } else {
                imageHtml = '<div class="product-card-image-placeholder">&#127803;</div>';
            }

            html += '<div class="product-card" data-product-id="' + p.id + '">'
                + imageHtml
                + '<div class="product-card-body">'
                + '  <div class="product-card-name">' + escapeHtml(p.name) + '</div>'
                + '  <div class="product-card-price">' + formatPrice(p.price) + '</div>'
                + '  <button class="btn-add-cart" data-product-id="' + p.id + '"'
                + '    data-product-name="' + escapeHtml(p.name) + '"'
                + '    data-product-price="' + p.price + '">'
                + '    + В корзину'
                + '  </button>'
                + '</div>'
                + '</div>';
        }

        dom.productsGrid.innerHTML = html;

        // Attach event handlers
        var cards = dom.productsGrid.querySelectorAll('.product-card');
        for (var i = 0; i < cards.length; i++) {
            cards[i].addEventListener('click', onProductCardClick);
        }

        var addBtns = dom.productsGrid.querySelectorAll('.btn-add-cart');
        for (var i = 0; i < addBtns.length; i++) {
            addBtns[i].addEventListener('click', onAddToCartClick);
        }
    }

    function onProductCardClick(e) {
        // Don't navigate if clicking the add-to-cart button
        if (e.target.closest('.btn-add-cart')) return;
        var productId = e.currentTarget.dataset.productId;
        viewProduct(productId);
    }

    function onAddToCartClick(e) {
        e.stopPropagation();
        var btn = e.currentTarget;
        var productId = parseInt(btn.dataset.productId, 10);
        var productName = btn.dataset.productName;
        var productPrice = parseFloat(btn.dataset.productPrice);

        addToCart({
            product_id: productId,
            product_name: productName,
            product_price: productPrice,
            quantity: 1,
        });

        // Visual feedback
        btn.classList.add('added');
        btn.textContent = 'Добавлено';
        setTimeout(function () {
            btn.classList.remove('added');
            btn.textContent = '+ В корзину';
        }, 1200);
    }

    // -------------------------------------------------------------------------
    // Product Detail
    // -------------------------------------------------------------------------

    function renderProductDetail(product) {
        var imageHtml = '';
        if (product.image_url) {
            imageHtml = '<img class="product-detail-image" src="'
                + escapeHtml(product.image_url) + '" alt="'
                + escapeHtml(product.name)
                + '" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';">'
                + '<div class="product-detail-image-placeholder" style="display:none;">&#127803;</div>';
        } else {
            imageHtml = '<div class="product-detail-image-placeholder">&#127803;</div>';
        }

        var html = imageHtml
            + '<div class="product-detail-info">'
            + '  <div class="product-detail-name">' + escapeHtml(product.name) + '</div>'
            + '  <div class="product-detail-price">' + formatPrice(product.price) + '</div>';

        if (product.description) {
            html += '<div class="product-detail-description">' + escapeHtml(product.description) + '</div>';
        }

        html += '  <button class="btn-add-cart-lg" id="detailAddToCartBtn">'
            + '    + Добавить в корзину'
            + '  </button>'
            + '  <div class="availability-section">'
            + '    <div class="availability-title">Наличие в магазинах</div>'
            + '    <div id="availabilityContent">'
            + '      <div class="availability-loading"><div class="spinner"></div> Загрузка...</div>'
            + '    </div>'
            + '  </div>'
            + '</div>';

        dom.productDetail.innerHTML = html;

        // Add to cart button
        var addBtn = document.getElementById('detailAddToCartBtn');
        addBtn.addEventListener('click', function () {
            addToCart({
                product_id: product.id,
                product_name: product.name,
                product_price: product.price,
                quantity: 1,
            });
            addBtn.classList.add('added');
            addBtn.textContent = 'Добавлено!';
            setTimeout(function () {
                addBtn.classList.remove('added');
                addBtn.textContent = '+ Добавить в корзину';
            }, 1200);
        });

        // Load availability
        loadAvailability(product.id);
    }

    async function loadAvailability(productId) {
        var container = document.getElementById('availabilityContent');
        if (!container) return;

        try {
            var data = await apiFetch('/catalog/products/' + productId + '/availability/');
            var availList = data || [];

            if (availList.length === 0) {
                container.innerHTML = '<div class="availability-empty">Нет информации о наличии</div>';
                return;
            }

            var html = '<div class="store-list">';
            for (var i = 0; i < availList.length; i++) {
                var avail = availList[i];
                var store = avail.store || {};
                var inStock = avail.quantity > 0;
                var qtyClass = inStock ? 'in-stock' : 'out-of-stock';
                var qtyText = inStock ? ('В наличии: ' + avail.quantity) : 'Нет в наличии';

                html += '<div class="store-item">'
                    + '  <div class="store-item-info">'
                    + '    <div class="store-item-name">' + escapeHtml(store.name || 'Магазин #' + avail.store_id) + '</div>';
                if (store.address) {
                    html += '    <div class="store-item-address">' + escapeHtml(store.address) + '</div>';
                }
                html += '  </div>'
                    + '  <span class="store-item-quantity ' + qtyClass + '">' + qtyText + '</span>'
                    + '</div>';
            }
            html += '</div>';

            container.innerHTML = html;
        } catch (err) {
            console.error('Failed to load availability:', err);
            container.innerHTML = '<div class="availability-empty">Не удалось загрузить наличие</div>';
        }
    }

    // -------------------------------------------------------------------------
    // Cart
    // -------------------------------------------------------------------------

    async function loadCart() {
        var userId = getUserId();
        if (!userId) {
            renderCartEmpty();
            return;
        }

        dom.cartLoading.style.display = 'flex';
        dom.cartContent.style.display = 'none';
        dom.cartEmpty.style.display = 'none';

        try {
            var data = await apiFetch('/orders/cart/' + userId + '/');
            state.cart = data;
        } catch (err) {
            console.error('Failed to load cart:', err);
            state.cart = null;
        }

        dom.cartLoading.style.display = 'none';
        renderCart();
    }

    async function addToCart(item) {
        var userId = getUserId();
        if (!userId) {
            showToast('Не удалось определить пользователя', 'error');
            return;
        }

        try {
            await apiFetch('/orders/cart/' + userId + '/items/', {
                method: 'POST',
                body: item,
            });
            showToast('Товар добавлен в корзину', 'success');

            // Refresh cart count
            refreshCartBadge();
        } catch (err) {
            console.error('Failed to add to cart:', err);
            showToast('Не удалось добавить товар', 'error');
        }
    }

    async function updateCartItem(itemId, quantity) {
        var userId = getUserId();
        if (!userId) return;

        try {
            await apiFetch('/orders/cart/' + userId + '/items/' + itemId + '/', {
                method: 'PUT',
                body: { quantity: quantity },
            });
            await loadCart();
        } catch (err) {
            console.error('Failed to update cart item:', err);
            showToast('Не удалось обновить количество', 'error');
        }
    }

    async function removeCartItem(itemId) {
        var userId = getUserId();
        if (!userId) return;

        try {
            await apiFetch('/orders/cart/' + userId + '/items/' + itemId + '/', {
                method: 'DELETE',
            });
            showToast('Товар удалён из корзины');
            await loadCart();
            refreshCartBadge();
        } catch (err) {
            console.error('Failed to remove cart item:', err);
            showToast('Не удалось удалить товар', 'error');
        }
    }

    async function refreshCartBadge() {
        var userId = getUserId();
        if (!userId) {
            updateCartBadge(0);
            return;
        }

        try {
            var data = await apiFetch('/orders/cart/' + userId + '/');
            state.cart = data;
            var count = 0;
            if (data && data.items) {
                for (var i = 0; i < data.items.length; i++) {
                    count += data.items[i].quantity;
                }
            }
            updateCartBadge(count);
        } catch (_err) {
            // Cart might not exist yet, that's ok
            updateCartBadge(0);
        }
    }

    function updateCartBadge(count) {
        dom.cartBadge.textContent = count;
        dom.cartBadge.classList.toggle('visible', count > 0);
    }

    function renderCart() {
        var items = (state.cart && state.cart.items) ? state.cart.items : [];

        if (items.length === 0) {
            renderCartEmpty();
            return;
        }

        dom.cartEmpty.style.display = 'none';
        dom.cartContent.style.display = 'block';

        var total = 0;
        var totalItems = 0;
        var itemsHtml = '';

        for (var i = 0; i < items.length; i++) {
            var item = items[i];
            var subtotal = item.product_price * item.quantity;
            total += subtotal;
            totalItems += item.quantity;

            itemsHtml += '<div class="cart-item" data-item-id="' + item.id + '">'
                + '  <div class="cart-item-image-placeholder">&#127803;</div>'
                + '  <div class="cart-item-info">'
                + '    <div class="cart-item-name">' + escapeHtml(item.product_name) + '</div>'
                + '    <div class="cart-item-price">' + formatPrice(item.product_price) + ' / шт.</div>'
                + '    <div class="cart-item-subtotal">' + formatPrice(subtotal) + '</div>'
                + '  </div>'
                + '  <div class="cart-item-controls">'
                + '    <button class="cart-qty-btn'
                + (item.quantity <= 1 ? ' remove' : '')
                + '" data-action="decrease" data-item-id="' + item.id
                + '" data-quantity="' + item.quantity + '">'
                + (item.quantity <= 1 ? '&#128465;' : '&minus;')
                + '</button>'
                + '    <span class="cart-qty-value">' + item.quantity + '</span>'
                + '    <button class="cart-qty-btn" data-action="increase" data-item-id="' + item.id
                + '" data-quantity="' + item.quantity + '">+</button>'
                + '  </div>'
                + '</div>';
        }

        var html = '<div class="cart-items-list">' + itemsHtml + '</div>'
            + '<div class="cart-summary">'
            + '  <div class="cart-summary-row">'
            + '    <span>Товаров</span>'
            + '    <span>' + totalItems + ' шт.</span>'
            + '  </div>'
            + '  <div class="cart-summary-row total">'
            + '    <span>Итого</span>'
            + '    <span>' + formatPrice(total) + '</span>'
            + '  </div>'
            + '</div>'
            + '<button class="cart-checkout-btn" id="cartCheckoutBtn">Перейти к оформлению</button>';

        dom.cartContent.innerHTML = html;

        // Update badge
        updateCartBadge(totalItems);

        // Attach cart item controls
        var qtyBtns = dom.cartContent.querySelectorAll('.cart-qty-btn');
        for (var i = 0; i < qtyBtns.length; i++) {
            qtyBtns[i].addEventListener('click', onCartQtyClick);
        }

        // Checkout button
        var checkoutBtn = document.getElementById('cartCheckoutBtn');
        if (checkoutBtn) {
            checkoutBtn.addEventListener('click', function () {
                navigateTo('checkout');
            });
        }
    }

    function renderCartEmpty() {
        dom.cartContent.style.display = 'none';
        dom.cartEmpty.style.display = 'flex';
        updateCartBadge(0);
    }

    function onCartQtyClick(e) {
        var btn = e.currentTarget;
        var action = btn.dataset.action;
        var itemId = btn.dataset.itemId;
        var currentQty = parseInt(btn.dataset.quantity, 10);

        if (action === 'increase') {
            updateCartItem(itemId, currentQty + 1);
        } else if (action === 'decrease') {
            if (currentQty <= 1) {
                removeCartItem(itemId);
            } else {
                updateCartItem(itemId, currentQty - 1);
            }
        }
    }

    // -------------------------------------------------------------------------
    // Checkout
    // -------------------------------------------------------------------------

    async function loadStores() {
        if (state.stores.length > 0) return;
        try {
            var data = await apiFetch('/catalog/stores/');
            state.stores = data || [];
        } catch (err) {
            console.error('Failed to load stores:', err);
            state.stores = [];
        }
    }

    function renderCheckout() {
        var items = (state.cart && state.cart.items) ? state.cart.items : [];

        if (items.length === 0) {
            dom.checkoutContent.innerHTML = '<div class="empty-state">'
                + '<p>Корзина пуста. Добавьте товары перед оформлением.</p>'
                + '<button class="btn btn-primary" id="checkoutGoToCatalog">Перейти в каталог</button>'
                + '</div>';
            var btn = document.getElementById('checkoutGoToCatalog');
            if (btn) btn.addEventListener('click', function () { navigateTo('catalog'); });
            return;
        }

        // Calculate total
        var total = 0;
        for (var i = 0; i < items.length; i++) {
            total += items[i].product_price * items[i].quantity;
        }

        // Order summary
        var orderSummaryHtml = '<div class="checkout-order-summary">';
        for (var i = 0; i < items.length; i++) {
            var item = items[i];
            orderSummaryHtml += '<div class="checkout-order-item">'
                + '  <span class="checkout-order-item-name">' + escapeHtml(item.product_name) + '</span>'
                + '  <span class="checkout-order-item-qty">' + item.quantity + ' шт.</span>'
                + '  <span class="checkout-order-item-price">' + formatPrice(item.product_price * item.quantity) + '</span>'
                + '</div>';
        }
        orderSummaryHtml += '<div class="checkout-total-row">'
            + '  <span>Итого</span>'
            + '  <span>' + formatPrice(total) + '</span>'
            + '</div></div>';

        var html = ''
            // Step 1: Order summary
            + '<div class="checkout-section">'
            + '  <div class="checkout-section-title"><span class="step-num">1</span> Ваш заказ</div>'
            + orderSummaryHtml
            + '</div>'

            // Step 2: Delivery type
            + '<div class="checkout-section">'
            + '  <div class="checkout-section-title"><span class="step-num">2</span> Способ получения</div>'
            + '  <div class="delivery-toggle">'
            + '    <button class="delivery-option' + (state.deliveryType === 'pickup' ? ' active' : '')
            + '" data-type="pickup">Самовывоз</button>'
            + '    <button class="delivery-option' + (state.deliveryType === 'delivery' ? ' active' : '')
            + '" data-type="delivery">Доставка</button>'
            + '  </div>'
            + '</div>'

            // Step 3: Details (dynamic based on delivery type)
            + '<div class="checkout-section" id="checkoutDetailsSection">'
            + '  <div class="checkout-section-title"><span class="step-num">3</span> Детали</div>'
            + '  <div id="checkoutDetailsContent"></div>'
            + '</div>';

        dom.checkoutContent.innerHTML = html;

        // Attach delivery toggle
        var deliveryOptions = dom.checkoutContent.querySelectorAll('.delivery-option');
        for (var i = 0; i < deliveryOptions.length; i++) {
            deliveryOptions[i].addEventListener('click', onDeliveryTypeChange);
        }

        // Render details section
        renderCheckoutDetails();

        // Show MainButton
        showMainButton('Оформить заказ', onSubmitOrder);
    }

    function onDeliveryTypeChange(e) {
        var type = e.currentTarget.dataset.type;
        state.deliveryType = type;

        // Update toggle
        var options = dom.checkoutContent.querySelectorAll('.delivery-option');
        for (var i = 0; i < options.length; i++) {
            options[i].classList.toggle('active', options[i].dataset.type === type);
        }

        renderCheckoutDetails();
    }

    async function renderCheckoutDetails() {
        var container = document.getElementById('checkoutDetailsContent');
        if (!container) return;

        if (state.deliveryType === 'pickup') {
            // Load stores if needed
            await loadStores();
            renderPickupDetails(container);
        } else {
            renderDeliveryDetails(container);
        }
    }

    function renderPickupDetails(container) {
        var html = '';

        // Store selector
        if (state.stores.length === 0) {
            html += '<div class="availability-empty">Нет доступных магазинов</div>';
        } else {
            html += '<div class="form-group">'
                + '  <label class="form-label">Выберите магазин</label>'
                + '  <div class="store-selector" id="storeSelector">';

            for (var i = 0; i < state.stores.length; i++) {
                var store = state.stores[i];
                var selected = state.selectedStoreId === store.id;
                html += '<div class="store-selector-item' + (selected ? ' selected' : '')
                    + '" data-store-id="' + store.id + '">'
                    + '  <div class="store-radio"></div>'
                    + '  <div class="store-selector-info">'
                    + '    <div class="store-selector-name">' + escapeHtml(store.name) + '</div>';
                if (store.address) {
                    html += '    <div class="store-selector-address">' + escapeHtml(store.address) + '</div>';
                }
                if (store.phone) {
                    html += '    <div class="store-selector-phone">' + escapeHtml(store.phone) + '</div>';
                }
                html += '  </div></div>';
            }

            html += '  </div></div>';
        }

        // Time picker
        html += '<div class="form-group">'
            + '  <label class="form-label">Время для сборки заказа</label>'
            + '  <div class="time-picker-row">'
            + '    <input type="date" class="form-input" id="pickupDate" value="' + getTodayDate() + '" min="' + getTodayDate() + '">'
            + '    <input type="time" class="form-input" id="pickupTime" value="' + (state.pickupTime || '') + '" placeholder="Время">'
            + '  </div>'
            + '</div>';

        container.innerHTML = html;

        // Attach store selector handlers
        var storeItems = container.querySelectorAll('.store-selector-item');
        for (var i = 0; i < storeItems.length; i++) {
            storeItems[i].addEventListener('click', onStoreSelect);
        }

        // Attach time change handler
        var pickupTimeInput = document.getElementById('pickupTime');
        if (pickupTimeInput) {
            pickupTimeInput.addEventListener('change', function (e) {
                state.pickupTime = e.target.value;
            });
        }
    }

    function renderDeliveryDetails(container) {
        var userAddress = '';
        if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
            // If address was previously entered, use it
            userAddress = state.deliveryAddress || '';
        }

        var html = '<div class="map-hint">'
            + '  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
            + '    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>'
            + '    <circle cx="12" cy="10" r="3"/>'
            + '  </svg>'
            + '  Укажите адрес доставки или отправьте местоположение через бот'
            + '</div>'
            + '<div class="form-group">'
            + '  <label class="form-label">Адрес доставки</label>'
            + '  <textarea class="form-textarea" id="deliveryAddressInput" '
            + '    placeholder="Введите адрес доставки">' + escapeHtml(userAddress) + '</textarea>'
            + '</div>';

        container.innerHTML = html;

        // Attach change handler
        var addressInput = document.getElementById('deliveryAddressInput');
        if (addressInput) {
            addressInput.addEventListener('input', function (e) {
                state.deliveryAddress = e.target.value;
            });
        }
    }

    function onStoreSelect(e) {
        var storeId = parseInt(e.currentTarget.dataset.storeId, 10);
        state.selectedStoreId = storeId;

        // Update visual state
        var storeItems = document.querySelectorAll('.store-selector-item');
        for (var i = 0; i < storeItems.length; i++) {
            storeItems[i].classList.toggle('selected',
                parseInt(storeItems[i].dataset.storeId, 10) === storeId);
        }
    }

    function getTodayDate() {
        var now = new Date();
        var yyyy = now.getFullYear();
        var mm = String(now.getMonth() + 1).padStart(2, '0');
        var dd = String(now.getDate()).padStart(2, '0');
        return yyyy + '-' + mm + '-' + dd;
    }

    // -------------------------------------------------------------------------
    // Submit Order
    // -------------------------------------------------------------------------

    async function onSubmitOrder() {
        var items = (state.cart && state.cart.items) ? state.cart.items : [];
        if (items.length === 0) {
            showToast('Корзина пуста', 'error');
            return;
        }

        // Validate
        if (state.deliveryType === 'pickup') {
            if (!state.selectedStoreId) {
                showToast('Выберите магазин для самовывоза', 'error');
                return;
            }
            var pickupTimeInput = document.getElementById('pickupTime');
            var pickupDateInput = document.getElementById('pickupDate');
            if (!pickupTimeInput || !pickupTimeInput.value) {
                showToast('Укажите время для сборки заказа', 'error');
                return;
            }
        } else {
            var addressInput = document.getElementById('deliveryAddressInput');
            if (!addressInput || !addressInput.value.trim()) {
                showToast('Укажите адрес доставки', 'error');
                return;
            }
        }

        setMainButtonLoading(true);

        // Build order data
        var orderItems = [];
        for (var i = 0; i < items.length; i++) {
            orderItems.push({
                product_id: items[i].product_id,
                product_name: items[i].product_name,
                product_price: items[i].product_price,
                quantity: items[i].quantity,
            });
        }

        var pickupTimeStr = '';
        if (state.deliveryType === 'pickup') {
            var dateInput = document.getElementById('pickupDate');
            var timeInput = document.getElementById('pickupTime');
            pickupTimeStr = (dateInput ? dateInput.value : '') + ' ' + (timeInput ? timeInput.value : '');
        }

        var orderData = {
            user_id: getUserId(),
            delivery_type: state.deliveryType,
            items: orderItems,
        };

        if (state.deliveryType === 'pickup') {
            orderData.store_id = state.selectedStoreId;
            orderData.pickup_time = pickupTimeStr.trim();
        } else {
            orderData.address = state.deliveryAddress;
        }

        try {
            var order = await apiFetch('/orders/orders/', {
                method: 'POST',
                body: orderData,
            });

            showToast('Заказ успешно оформлен!', 'success');

            // Send order data back to Telegram bot
            if (tg && tg.sendData) {
                tg.sendData(JSON.stringify({
                    action: 'order_created',
                    order_id: order.id,
                    delivery_type: state.deliveryType,
                    total: order.total_amount,
                }));
            }

            // Reset state
            state.cart = null;
            state.selectedStoreId = null;
            state.pickupTime = '';
            state.deliveryAddress = '';
            updateCartBadge(0);
            hideMainButton();

            // Show success message in checkout content
            dom.checkoutContent.innerHTML = '<div class="empty-state">'
                + '  <div style="font-size:64px; margin-bottom:16px;">&#127881;</div>'
                + '  <h2 style="margin-bottom:8px;">Заказ оформлен!</h2>'
                + '  <p style="margin-bottom:20px;">Заказ #' + order.id + ' успешно создан.</p>'
                + '  <button class="btn btn-primary" id="backToCatalogAfterOrder">Вернуться в каталог</button>'
                + '</div>';

            var backBtn = document.getElementById('backToCatalogAfterOrder');
            if (backBtn) {
                backBtn.addEventListener('click', function () { navigateTo('catalog'); });
            }

        } catch (err) {
            console.error('Failed to submit order:', err);
            showToast('Не удалось оформить заказ: ' + err.message, 'error');
        }

        setMainButtonLoading(false);
    }

    // -------------------------------------------------------------------------
    // Event listeners
    // -------------------------------------------------------------------------

    function initEventListeners() {
        // Navigation tabs
        var tabs = $$('.nav-tab');
        for (var i = 0; i < tabs.length; i++) {
            tabs[i].addEventListener('click', function (e) {
                var view = e.currentTarget.dataset.view;
                navigateTo(view);
            });
        }

        // Header cart button
        dom.headerCartBtn.addEventListener('click', function () {
            navigateTo('cart');
        });

        // Go to catalog from empty cart
        if (dom.goToCatalogBtn) {
            dom.goToCatalogBtn.addEventListener('click', function () {
                navigateTo('catalog');
            });
        }

        // Telegram BackButton
        if (tg && tg.BackButton) {
            tg.BackButton.onClick(goBack);
        }

        // Error retry
        dom.errorRetryBtn.addEventListener('click', function () {
            dom.errorOverlay.style.display = 'none';
            init();
        });
    }

    // -------------------------------------------------------------------------
    // Initialization
    // -------------------------------------------------------------------------

    async function init() {
        initEventListeners();

        // Load initial data in parallel
        await Promise.all([
            loadCategories(),
            loadProducts(),
            refreshCartBadge(),
        ]);
    }

    // Start the app
    init();

})();
