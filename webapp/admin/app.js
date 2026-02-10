/* ==========================================================================
   Admin Panel - Telegram Mini App
   Vanilla JS application for managing a flower shop
   ========================================================================== */

'use strict';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
var API_BASE = '/api';

// ---------------------------------------------------------------------------
// Telegram WebApp Initialization
// ---------------------------------------------------------------------------
var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

if (tg) {
  tg.ready();
  tg.expand();
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
var state = {
  products: [],
  categories: [],
  stores: [],
  orders: [],
  dashboard: null,
  popularByViews: [],
  popularByOrders: [],
  activeTab: 'products',
  selectedStoreId: null,
  availabilityMap: {}  // { "storeId-productId": quantity }
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Show a toast notification.
 * @param {string} message
 * @param {'success'|'error'|'info'} type
 */
function showToast(message, type) {
  type = type || 'info';
  var container = document.getElementById('toastContainer');
  var toast = document.createElement('div');
  toast.className = 'toast toast--' + type;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(function () {
    if (toast.parentNode) {
      toast.parentNode.removeChild(toast);
    }
  }, 3000);
}

/**
 * Generic API fetch wrapper.
 * @param {string} url
 * @param {object} options
 * @returns {Promise<any>}
 */
function apiFetch(url, options) {
  options = options || {};
  options.headers = options.headers || {};
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  // Include Telegram initData if available for auth
  if (tg && tg.initData) {
    options.headers['X-Telegram-Init-Data'] = tg.initData;
  }

  return fetch(url, options)
    .then(function (response) {
      if (response.status === 204) {
        return null;
      }
      if (!response.ok) {
        return response.json().then(function (err) {
          throw new Error(err.detail || ('HTTP ' + response.status));
        }).catch(function (e) {
          if (e.message) throw e;
          throw new Error('HTTP ' + response.status);
        });
      }
      return response.json();
    });
}

/**
 * Format a number as Russian rubles.
 * @param {number} n
 * @returns {string}
 */
function formatPrice(n) {
  if (n == null) return '--';
  return Number(n).toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) + ' \u20BD';
}

/**
 * Format a date/datetime string for display.
 * @param {string} dateStr
 * @returns {string}
 */
function formatDate(dateStr) {
  if (!dateStr) return '--';
  var d = new Date(dateStr);
  return d.toLocaleDateString('ru-RU') + ' ' + d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

/**
 * Escape HTML entities.
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
  if (!str) return '';
  var div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Show a confirmation dialog. Uses Telegram popup if available, else native confirm.
 * @param {string} message
 * @returns {Promise<boolean>}
 */
function showConfirm(message) {
  if (tg && tg.showConfirm) {
    return new Promise(function (resolve) {
      tg.showConfirm(message, function (confirmed) {
        resolve(confirmed);
      });
    });
  }
  return Promise.resolve(confirm(message));
}

/**
 * Get the category name by ID.
 * @param {number} categoryId
 * @returns {string}
 */
function getCategoryName(categoryId) {
  for (var i = 0; i < state.categories.length; i++) {
    if (state.categories[i].id === categoryId) {
      return state.categories[i].name;
    }
  }
  return 'Без категории';
}

/**
 * Get status label in Russian.
 * @param {string} status
 * @returns {string}
 */
function getStatusLabel(status) {
  var labels = {
    'pending': 'Ожидает',
    'processing': 'В обработке',
    'completed': 'Выполнен',
    'cancelled': 'Отменён'
  };
  return labels[status] || status;
}

/**
 * Get delivery type label in Russian.
 * @param {string} type
 * @returns {string}
 */
function getDeliveryLabel(type) {
  var labels = {
    'pickup': 'Самовывоз',
    'delivery': 'Доставка'
  };
  return labels[type] || type;
}

// ---------------------------------------------------------------------------
// API Functions - Products
// ---------------------------------------------------------------------------

function loadProducts() {
  return apiFetch(API_BASE + '/catalog/products/')
    .then(function (data) {
      state.products = data || [];
      return state.products;
    });
}

function loadCategories() {
  return apiFetch(API_BASE + '/catalog/categories/')
    .then(function (data) {
      state.categories = data || [];
      return state.categories;
    });
}

function addProduct(data) {
  return apiFetch(API_BASE + '/catalog/products/', {
    method: 'POST',
    body: data
  });
}

function updateProduct(id, data) {
  return apiFetch(API_BASE + '/catalog/products/' + id, {
    method: 'PUT',
    body: data
  });
}

function deleteProduct(id) {
  return apiFetch(API_BASE + '/catalog/products/' + id, {
    method: 'DELETE'
  });
}

function addCategory(data) {
  return apiFetch(API_BASE + '/catalog/categories/', {
    method: 'POST',
    body: data
  });
}

function updateCategory(id, data) {
  return apiFetch(API_BASE + '/catalog/categories/' + id, {
    method: 'PUT',
    body: data
  });
}

function deleteCategory(id) {
  return apiFetch(API_BASE + '/catalog/categories/' + id, {
    method: 'DELETE'
  });
}

// ---------------------------------------------------------------------------
// API Functions - Availability
// ---------------------------------------------------------------------------

function loadStores() {
  return apiFetch(API_BASE + '/catalog/stores/')
    .then(function (data) {
      state.stores = data || [];
      return state.stores;
    });
}

function loadProductAvailability(productId) {
  return apiFetch(API_BASE + '/catalog/products/' + productId + '/availability');
}

function setAvailability(storeId, productId, quantity) {
  return apiFetch(API_BASE + '/catalog/stores/' + storeId + '/products/' + productId + '/availability', {
    method: 'POST',
    body: { quantity: quantity }
  });
}

// ---------------------------------------------------------------------------
// API Functions - Orders
// ---------------------------------------------------------------------------

function loadOrders() {
  return apiFetch(API_BASE + '/orders/orders/')
    .then(function (data) {
      state.orders = data || [];
      return state.orders;
    });
}

function updateOrderStatus(orderId, status) {
  return apiFetch(API_BASE + '/orders/orders/' + orderId + '/status', {
    method: 'PUT',
    body: { status: status }
  });
}

// ---------------------------------------------------------------------------
// API Functions - Analytics
// ---------------------------------------------------------------------------

function loadDashboard() {
  return apiFetch(API_BASE + '/analytics/analytics/dashboard')
    .then(function (data) {
      state.dashboard = data;
      return data;
    });
}

function loadPopularByViews() {
  return apiFetch(API_BASE + '/analytics/analytics/popular/views')
    .then(function (data) {
      state.popularByViews = data || [];
      return data;
    });
}

function loadPopularByOrders() {
  return apiFetch(API_BASE + '/analytics/analytics/popular/orders')
    .then(function (data) {
      state.popularByOrders = data || [];
      return data;
    });
}

// ---------------------------------------------------------------------------
// Render - Categories
// ---------------------------------------------------------------------------

function renderCategoriesList() {
  var container = document.getElementById('categoriesList');
  if (!state.categories.length) {
    container.innerHTML = '<div class="empty-state">Нет категорий</div>';
    return;
  }
  var html = '';
  for (var i = 0; i < state.categories.length; i++) {
    var cat = state.categories[i];
    html += '<div class="category-item" data-id="' + cat.id + '">'
      + '<div class="category-item__info">'
      + '<div class="category-item__name">' + escapeHtml(cat.name) + '</div>'
      + (cat.description ? '<div class="category-item__desc">' + escapeHtml(cat.description) + '</div>' : '')
      + '</div>'
      + '<div class="category-item__actions">'
      + '<button class="btn btn--small btn--secondary btn-edit-category" data-id="' + cat.id + '">Изм.</button>'
      + '<button class="btn btn--small btn--danger btn-delete-category" data-id="' + cat.id + '">Уд.</button>'
      + '</div>'
      + '</div>';
  }
  container.innerHTML = html;
}

function populateCategorySelects() {
  var selects = [
    document.getElementById('productCategory'),
    document.getElementById('filterCategory')
  ];
  for (var s = 0; s < selects.length; s++) {
    var sel = selects[s];
    if (!sel) continue;
    // Keep the first option
    var first = sel.options[0];
    sel.innerHTML = '';
    sel.appendChild(first);
    for (var i = 0; i < state.categories.length; i++) {
      var opt = document.createElement('option');
      opt.value = state.categories[i].id;
      opt.textContent = state.categories[i].name;
      sel.appendChild(opt);
    }
  }
}

// ---------------------------------------------------------------------------
// Render - Products Manager
// ---------------------------------------------------------------------------

function renderProductsManager() {
  var container = document.getElementById('productsList');
  var filterCategoryId = document.getElementById('filterCategory').value;
  var products = state.products;

  if (filterCategoryId) {
    products = products.filter(function (p) {
      return String(p.category_id) === String(filterCategoryId);
    });
  }

  if (!products.length) {
    container.innerHTML = '<div class="empty-state">Нет товаров' + (filterCategoryId ? ' в этой категории' : '') + '</div>';
    return;
  }

  var html = '';
  for (var i = 0; i < products.length; i++) {
    var p = products[i];
    var imgHtml;
    if (p.image_url) {
      imgHtml = '<img class="product-card__image" src="' + escapeHtml(p.image_url) + '" alt="' + escapeHtml(p.name) + '" onerror="this.style.display=\'none\'">';
    } else {
      imgHtml = '<div class="product-card__image--placeholder">&#127803;</div>';
    }

    html += '<div class="product-card" data-id="' + p.id + '">'
      + imgHtml
      + '<div class="product-card__info">'
      + '<div class="product-card__name">' + escapeHtml(p.name) + '</div>'
      + '<div class="product-card__category">' + escapeHtml(getCategoryName(p.category_id)) + '</div>'
      + '<div class="product-card__price">' + formatPrice(p.price) + '</div>'
      + '</div>'
      + '<div class="product-card__actions">'
      + '<button class="btn btn--small btn--secondary btn-edit-product" data-id="' + p.id + '">Изм.</button>'
      + '<button class="btn btn--small btn--danger btn-delete-product" data-id="' + p.id + '">Уд.</button>'
      + '</div>'
      + '</div>';
  }
  container.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Render - Availability Manager
// ---------------------------------------------------------------------------

function renderAvailabilityManager() {
  var container = document.getElementById('availabilityList');
  var storeId = state.selectedStoreId;

  if (!storeId) {
    container.innerHTML = '<div class="empty-state">Выберите магазин для просмотра наличия</div>';
    return;
  }

  if (!state.products.length) {
    container.innerHTML = '<div class="empty-state">Нет товаров в каталоге</div>';
    return;
  }

  container.innerHTML = '<div class="loading">Загрузка наличия...</div>';

  // Load availability for all products in parallel
  var promises = state.products.map(function (product) {
    return loadProductAvailability(product.id)
      .then(function (avail) {
        // Find availability for this specific store
        var storeAvail = (avail || []).filter(function (a) {
          return String(a.store_id) === String(storeId);
        });
        var qty = storeAvail.length > 0 ? storeAvail[0].quantity : 0;
        state.availabilityMap[storeId + '-' + product.id] = qty;
      })
      .catch(function () {
        state.availabilityMap[storeId + '-' + product.id] = 0;
      });
  });

  Promise.all(promises).then(function () {
    renderAvailabilityList(storeId);
  });
}

function renderAvailabilityList(storeId) {
  var container = document.getElementById('availabilityList');
  var html = '';

  for (var i = 0; i < state.products.length; i++) {
    var p = state.products[i];
    var key = storeId + '-' + p.id;
    var qty = state.availabilityMap[key] || 0;

    html += '<div class="availability-item" data-product-id="' + p.id + '">'
      + '<div class="availability-item__info">'
      + '<div class="availability-item__name">' + escapeHtml(p.name) + '</div>'
      + '<div class="availability-item__price">' + formatPrice(p.price) + '</div>'
      + '</div>'
      + '<div class="availability-item__control">'
      + '<input type="number" class="availability-item__qty-input" '
      + 'data-store-id="' + storeId + '" data-product-id="' + p.id + '" '
      + 'value="' + qty + '" min="0" step="1">'
      + '<button class="btn btn--small btn--primary availability-item__save btn-save-availability" '
      + 'data-store-id="' + storeId + '" data-product-id="' + p.id + '">OK</button>'
      + '</div>'
      + '</div>';
  }

  container.innerHTML = html || '<div class="empty-state">Нет товаров</div>';
}

// ---------------------------------------------------------------------------
// Render - Orders Manager
// ---------------------------------------------------------------------------

function renderOrdersManager() {
  var container = document.getElementById('ordersList');
  var orders = state.orders;

  if (!orders.length) {
    container.innerHTML = '<div class="empty-state">Нет заказов</div>';
    return;
  }

  // Sort by date descending
  orders.sort(function (a, b) {
    return new Date(b.created_at) - new Date(a.created_at);
  });

  var html = '';
  for (var i = 0; i < orders.length; i++) {
    var o = orders[i];
    var statusClass = 'status-badge--' + (o.status || 'pending');

    html += '<div class="order-card" data-id="' + o.id + '">'
      + '<div class="order-card__header">'
      + '<span class="order-card__id">Заказ #' + o.id + '</span>'
      + '<span class="order-card__date">' + formatDate(o.created_at) + '</span>'
      + '</div>'
      + '<div class="order-card__body">'
      + '<div class="order-card__row">'
      + '<span class="order-card__row-label">Статус</span>'
      + '<span class="status-badge ' + statusClass + '">' + getStatusLabel(o.status) + '</span>'
      + '</div>'
      + '<div class="order-card__row">'
      + '<span class="order-card__row-label">Тип доставки</span>'
      + '<span>' + getDeliveryLabel(o.delivery_type) + '</span>'
      + '</div>';

    if (o.address) {
      html += '<div class="order-card__row">'
        + '<span class="order-card__row-label">Адрес</span>'
        + '<span>' + escapeHtml(o.address) + '</span>'
        + '</div>';
    }

    if (o.pickup_time) {
      html += '<div class="order-card__row">'
        + '<span class="order-card__row-label">Время самовывоза</span>'
        + '<span>' + escapeHtml(o.pickup_time) + '</span>'
        + '</div>';
    }

    html += '<div class="order-card__row">'
      + '<span class="order-card__row-label">Пользователь</span>'
      + '<span>' + o.user_id + '</span>'
      + '</div>';

    // Order items
    if (o.items && o.items.length) {
      html += '<div class="order-card__items">';
      for (var j = 0; j < o.items.length; j++) {
        var item = o.items[j];
        html += '<div class="order-card__item">'
          + '<span>' + escapeHtml(item.product_name) + ' x' + item.quantity + '</span>'
          + '<span>' + formatPrice(item.product_price * item.quantity) + '</span>'
          + '</div>';
      }
      html += '</div>';
    }

    html += '</div>'; // end body

    html += '<div class="order-card__footer">'
      + '<span class="order-card__total">' + formatPrice(o.total_amount) + '</span>'
      + '<select class="status-select order-status-select" data-order-id="' + o.id + '">'
      + '<option value="pending"' + (o.status === 'pending' ? ' selected' : '') + '>Ожидает</option>'
      + '<option value="processing"' + (o.status === 'processing' ? ' selected' : '') + '>В обработке</option>'
      + '<option value="completed"' + (o.status === 'completed' ? ' selected' : '') + '>Выполнен</option>'
      + '<option value="cancelled"' + (o.status === 'cancelled' ? ' selected' : '') + '>Отменён</option>'
      + '</select>'
      + '</div>';

    html += '</div>'; // end order-card
  }

  container.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Render - Dashboard / Metrics
// ---------------------------------------------------------------------------

function renderDashboard() {
  var d = state.dashboard;
  if (!d) {
    document.getElementById('statTotalOrders').textContent = '--';
    document.getElementById('statRevenue').textContent = '--';
    document.getElementById('statAvgOrder').textContent = '--';
    document.getElementById('statTodayOrders').textContent = '--';
    return;
  }

  document.getElementById('statTotalOrders').textContent = d.total_orders;
  document.getElementById('statRevenue').textContent = formatPrice(d.total_revenue);
  document.getElementById('statAvgOrder').textContent = formatPrice(d.avg_order_value);
  document.getElementById('statTodayOrders').textContent = d.orders_today;

  // Render popular by views from dashboard or separate call
  if (d.popular_by_views && d.popular_by_views.length) {
    state.popularByViews = d.popular_by_views;
  }
  if (d.popular_by_orders && d.popular_by_orders.length) {
    state.popularByOrders = d.popular_by_orders;
  }

  renderRankedList('popularByViews', state.popularByViews, 'view_count');
  renderRankedList('popularByOrders', state.popularByOrders, 'order_count');
}

function renderRankedList(containerId, items, countField) {
  var container = document.getElementById(containerId);
  if (!items || !items.length) {
    container.innerHTML = '<div class="empty-state">Нет данных</div>';
    return;
  }

  var maxCount = 1;
  for (var i = 0; i < items.length; i++) {
    if (items[i][countField] > maxCount) {
      maxCount = items[i][countField];
    }
  }

  var html = '';
  for (var j = 0; j < items.length; j++) {
    var item = items[j];
    var count = item[countField] || 0;
    var pct = maxCount > 0 ? Math.round((count / maxCount) * 100) : 0;

    html += '<div class="ranked-item">'
      + '<span class="ranked-item__rank">' + (j + 1) + '</span>'
      + '<div class="ranked-item__info">'
      + '<div class="ranked-item__name">' + escapeHtml(item.product_name) + '</div>'
      + '<div class="ranked-item__bar-container">'
      + '<div class="ranked-item__bar" style="width:' + pct + '%"></div>'
      + '</div>'
      + '</div>'
      + '<span class="ranked-item__count">' + count + '</span>'
      + '</div>';
  }

  container.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Modal Helpers
// ---------------------------------------------------------------------------

function openModal(modalId) {
  var modal = document.getElementById(modalId);
  if (modal) modal.classList.add('open');
}

function closeModal(modalId) {
  var modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('open');
}

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------

function switchTab(tabName) {
  state.activeTab = tabName;

  // Update tab buttons
  var buttons = document.querySelectorAll('.nav-tabs__btn');
  for (var i = 0; i < buttons.length; i++) {
    buttons[i].classList.toggle('active', buttons[i].getAttribute('data-tab') === tabName);
  }

  // Update tab content
  var sections = document.querySelectorAll('.tab-content');
  for (var j = 0; j < sections.length; j++) {
    sections[j].classList.toggle('active', sections[j].id === 'tab-' + tabName);
  }

  // Load data for active tab
  onTabActivated(tabName);

  // Handle Telegram BackButton
  if (tg && tg.BackButton) {
    if (tabName === 'products') {
      tg.BackButton.hide();
    } else {
      tg.BackButton.show();
    }
  }
}

function onTabActivated(tabName) {
  switch (tabName) {
    case 'products':
      refreshProductsTab();
      break;
    case 'availability':
      refreshAvailabilityTab();
      break;
    case 'orders':
      refreshOrdersTab();
      break;
    case 'metrics':
      refreshMetricsTab();
      break;
  }
}

// ---------------------------------------------------------------------------
// Tab Refresh Functions
// ---------------------------------------------------------------------------

function refreshProductsTab() {
  var productsContainer = document.getElementById('productsList');
  var categoriesContainer = document.getElementById('categoriesList');
  productsContainer.innerHTML = '<div class="loading">Загрузка...</div>';
  categoriesContainer.innerHTML = '<div class="loading">Загрузка...</div>';

  Promise.all([loadCategories(), loadProducts()])
    .then(function () {
      renderCategoriesList();
      populateCategorySelects();
      renderProductsManager();
    })
    .catch(function (err) {
      productsContainer.innerHTML = '<div class="error-state">Ошибка загрузки: ' + escapeHtml(err.message) + '</div>';
      categoriesContainer.innerHTML = '<div class="error-state">Ошибка загрузки</div>';
    });
}

function refreshAvailabilityTab() {
  var storeSelect = document.getElementById('filterStore');

  Promise.all([loadStores(), loadProducts()])
    .then(function () {
      // Populate store select
      var first = storeSelect.options[0];
      storeSelect.innerHTML = '';
      storeSelect.appendChild(first);
      for (var i = 0; i < state.stores.length; i++) {
        var opt = document.createElement('option');
        opt.value = state.stores[i].id;
        opt.textContent = state.stores[i].name + (state.stores[i].address ? ' (' + state.stores[i].address + ')' : '');
        storeSelect.appendChild(opt);
      }

      if (state.selectedStoreId) {
        storeSelect.value = state.selectedStoreId;
        renderAvailabilityManager();
      }
    })
    .catch(function (err) {
      document.getElementById('availabilityList').innerHTML =
        '<div class="error-state">Ошибка загрузки: ' + escapeHtml(err.message) + '</div>';
    });
}

function refreshOrdersTab() {
  var container = document.getElementById('ordersList');
  container.innerHTML = '<div class="loading">Загрузка...</div>';

  loadOrders()
    .then(function () {
      renderOrdersManager();
    })
    .catch(function (err) {
      container.innerHTML = '<div class="error-state">Ошибка загрузки: ' + escapeHtml(err.message) + '</div>';
    });
}

function refreshMetricsTab() {
  document.getElementById('popularByViews').innerHTML = '<div class="loading">Загрузка...</div>';
  document.getElementById('popularByOrders').innerHTML = '<div class="loading">Загрузка...</div>';

  Promise.all([loadDashboard(), loadPopularByViews(), loadPopularByOrders()])
    .then(function () {
      renderDashboard();
    })
    .catch(function (err) {
      document.getElementById('popularByViews').innerHTML =
        '<div class="error-state">Ошибка загрузки: ' + escapeHtml(err.message) + '</div>';
      document.getElementById('popularByOrders').innerHTML = '<div class="error-state">Ошибка загрузки</div>';
    });
}

// ---------------------------------------------------------------------------
// Event Handlers - Navigation
// ---------------------------------------------------------------------------

function initNavigation() {
  var tabButtons = document.querySelectorAll('.nav-tabs__btn');
  for (var i = 0; i < tabButtons.length; i++) {
    tabButtons[i].addEventListener('click', function () {
      switchTab(this.getAttribute('data-tab'));
    });
  }

  // Telegram BackButton handler
  if (tg && tg.BackButton) {
    tg.BackButton.onClick(function () {
      switchTab('products');
    });
  }
}

// ---------------------------------------------------------------------------
// Event Handlers - Categories
// ---------------------------------------------------------------------------

function initCategoryHandlers() {
  // Add category button
  document.getElementById('btnAddCategory').addEventListener('click', function () {
    document.getElementById('categoryFormTitle').textContent = 'Добавить категорию';
    document.getElementById('categoryId').value = '';
    document.getElementById('categoryName').value = '';
    document.getElementById('categoryDescription').value = '';
    openModal('categoryFormModal');
  });

  // Cancel category form
  document.getElementById('btnCancelCategory').addEventListener('click', function () {
    closeModal('categoryFormModal');
  });

  // Close modal on overlay click
  document.querySelector('#categoryFormModal .modal__overlay').addEventListener('click', function () {
    closeModal('categoryFormModal');
  });

  // Category form submit
  document.getElementById('categoryForm').addEventListener('submit', function (e) {
    e.preventDefault();
    var id = document.getElementById('categoryId').value;
    var data = {
      name: document.getElementById('categoryName').value.trim(),
      description: document.getElementById('categoryDescription').value.trim() || null
    };

    if (!data.name) {
      showToast('Введите название категории', 'error');
      return;
    }

    var btnSave = document.getElementById('btnSaveCategory');
    btnSave.disabled = true;

    var promise;
    if (id) {
      promise = updateCategory(id, data);
    } else {
      promise = addCategory(data);
    }

    promise
      .then(function () {
        closeModal('categoryFormModal');
        showToast(id ? 'Категория обновлена' : 'Категория добавлена', 'success');
        refreshProductsTab();
      })
      .catch(function (err) {
        showToast('Ошибка: ' + err.message, 'error');
      })
      .finally(function () {
        btnSave.disabled = false;
      });
  });

  // Delegate edit/delete category clicks
  document.getElementById('categoriesList').addEventListener('click', function (e) {
    var editBtn = e.target.closest('.btn-edit-category');
    var deleteBtn = e.target.closest('.btn-delete-category');

    if (editBtn) {
      var catId = editBtn.getAttribute('data-id');
      var cat = state.categories.find(function (c) { return String(c.id) === catId; });
      if (cat) {
        document.getElementById('categoryFormTitle').textContent = 'Редактировать категорию';
        document.getElementById('categoryId').value = cat.id;
        document.getElementById('categoryName').value = cat.name;
        document.getElementById('categoryDescription').value = cat.description || '';
        openModal('categoryFormModal');
      }
    }

    if (deleteBtn) {
      var delCatId = deleteBtn.getAttribute('data-id');
      showConfirm('Удалить категорию? Все товары в ней также будут удалены.').then(function (confirmed) {
        if (!confirmed) return;
        deleteCategory(delCatId)
          .then(function () {
            showToast('Категория удалена', 'success');
            refreshProductsTab();
          })
          .catch(function (err) {
            showToast('Ошибка: ' + err.message, 'error');
          });
      });
    }
  });
}

// ---------------------------------------------------------------------------
// Event Handlers - Products
// ---------------------------------------------------------------------------

function initProductHandlers() {
  // Add product button
  document.getElementById('btnAddProduct').addEventListener('click', function () {
    document.getElementById('productFormTitle').textContent = 'Добавить товар';
    document.getElementById('productId').value = '';
    document.getElementById('productName').value = '';
    document.getElementById('productDescription').value = '';
    document.getElementById('productPrice').value = '';
    document.getElementById('productImageUrl').value = '';
    document.getElementById('productCategory').value = '';
    openModal('productFormModal');
  });

  // Cancel product form
  document.getElementById('btnCancelProduct').addEventListener('click', function () {
    closeModal('productFormModal');
  });

  // Close modal on overlay click
  document.querySelector('#productFormModal .modal__overlay').addEventListener('click', function () {
    closeModal('productFormModal');
  });

  // Product form submit
  document.getElementById('productForm').addEventListener('submit', function (e) {
    e.preventDefault();
    var id = document.getElementById('productId').value;
    var data = {
      name: document.getElementById('productName').value.trim(),
      description: document.getElementById('productDescription').value.trim() || null,
      price: parseFloat(document.getElementById('productPrice').value),
      image_url: document.getElementById('productImageUrl').value.trim() || null,
      category_id: parseInt(document.getElementById('productCategory').value, 10)
    };

    if (!data.name) {
      showToast('Введите название товара', 'error');
      return;
    }
    if (isNaN(data.price) || data.price < 0) {
      showToast('Укажите корректную цену', 'error');
      return;
    }
    if (isNaN(data.category_id)) {
      showToast('Выберите категорию', 'error');
      return;
    }

    var btnSave = document.getElementById('btnSaveProduct');
    btnSave.disabled = true;

    var promise;
    if (id) {
      promise = updateProduct(id, data);
    } else {
      promise = addProduct(data);
    }

    promise
      .then(function () {
        closeModal('productFormModal');
        showToast(id ? 'Товар обновлён' : 'Товар добавлен', 'success');
        refreshProductsTab();
      })
      .catch(function (err) {
        showToast('Ошибка: ' + err.message, 'error');
      })
      .finally(function () {
        btnSave.disabled = false;
      });
  });

  // Delegate edit/delete product clicks
  document.getElementById('productsList').addEventListener('click', function (e) {
    var editBtn = e.target.closest('.btn-edit-product');
    var deleteBtn = e.target.closest('.btn-delete-product');

    if (editBtn) {
      var prodId = editBtn.getAttribute('data-id');
      var prod = state.products.find(function (p) { return String(p.id) === prodId; });
      if (prod) {
        document.getElementById('productFormTitle').textContent = 'Редактировать товар';
        document.getElementById('productId').value = prod.id;
        document.getElementById('productName').value = prod.name;
        document.getElementById('productDescription').value = prod.description || '';
        document.getElementById('productPrice').value = prod.price;
        document.getElementById('productImageUrl').value = prod.image_url || '';
        document.getElementById('productCategory').value = prod.category_id;
        openModal('productFormModal');
      }
    }

    if (deleteBtn) {
      var delProdId = deleteBtn.getAttribute('data-id');
      showConfirm('Удалить этот товар?').then(function (confirmed) {
        if (!confirmed) return;
        deleteProduct(delProdId)
          .then(function () {
            showToast('Товар удалён', 'success');
            refreshProductsTab();
          })
          .catch(function (err) {
            showToast('Ошибка: ' + err.message, 'error');
          });
      });
    }
  });

  // Filter by category
  document.getElementById('filterCategory').addEventListener('change', function () {
    renderProductsManager();
  });
}

// ---------------------------------------------------------------------------
// Event Handlers - Availability
// ---------------------------------------------------------------------------

function initAvailabilityHandlers() {
  // Store select change
  document.getElementById('filterStore').addEventListener('change', function () {
    state.selectedStoreId = this.value || null;
    if (state.selectedStoreId) {
      renderAvailabilityManager();
    } else {
      document.getElementById('availabilityList').innerHTML =
        '<div class="empty-state">Выберите магазин для просмотра наличия</div>';
    }
  });

  // Delegate save availability clicks
  document.getElementById('availabilityList').addEventListener('click', function (e) {
    var saveBtn = e.target.closest('.btn-save-availability');
    if (!saveBtn) return;

    var storeId = saveBtn.getAttribute('data-store-id');
    var productId = saveBtn.getAttribute('data-product-id');
    var input = document.querySelector(
      '.availability-item__qty-input[data-store-id="' + storeId + '"][data-product-id="' + productId + '"]'
    );
    if (!input) return;

    var quantity = parseInt(input.value, 10);
    if (isNaN(quantity) || quantity < 0) {
      showToast('Укажите корректное количество', 'error');
      return;
    }

    saveBtn.disabled = true;
    setAvailability(storeId, productId, quantity)
      .then(function () {
        state.availabilityMap[storeId + '-' + productId] = quantity;
        showToast('Наличие обновлено', 'success');
      })
      .catch(function (err) {
        showToast('Ошибка: ' + err.message, 'error');
      })
      .finally(function () {
        saveBtn.disabled = false;
      });
  });

  // Allow Enter key in quantity inputs to trigger save
  document.getElementById('availabilityList').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && e.target.classList.contains('availability-item__qty-input')) {
      e.preventDefault();
      var storeId = e.target.getAttribute('data-store-id');
      var productId = e.target.getAttribute('data-product-id');
      var saveBtn = document.querySelector(
        '.btn-save-availability[data-store-id="' + storeId + '"][data-product-id="' + productId + '"]'
      );
      if (saveBtn) saveBtn.click();
    }
  });
}

// ---------------------------------------------------------------------------
// Event Handlers - Orders
// ---------------------------------------------------------------------------

function initOrderHandlers() {
  // Refresh button
  document.getElementById('btnRefreshOrders').addEventListener('click', function () {
    refreshOrdersTab();
  });

  // Delegate order status change
  document.getElementById('ordersList').addEventListener('change', function (e) {
    if (!e.target.classList.contains('order-status-select')) return;

    var orderId = e.target.getAttribute('data-order-id');
    var newStatus = e.target.value;

    showConfirm('Изменить статус заказа #' + orderId + ' на "' + getStatusLabel(newStatus) + '"?')
      .then(function (confirmed) {
        if (!confirmed) {
          // Revert to previous value
          var order = state.orders.find(function (o) { return String(o.id) === orderId; });
          if (order) e.target.value = order.status;
          return;
        }

        e.target.disabled = true;
        updateOrderStatus(orderId, newStatus)
          .then(function () {
            showToast('Статус обновлён', 'success');
            refreshOrdersTab();
          })
          .catch(function (err) {
            showToast('Ошибка: ' + err.message, 'error');
            // Revert
            var order = state.orders.find(function (o) { return String(o.id) === orderId; });
            if (order) e.target.value = order.status;
          })
          .finally(function () {
            e.target.disabled = false;
          });
      });
  });
}

// ---------------------------------------------------------------------------
// Event Handlers - Metrics
// ---------------------------------------------------------------------------

function initMetricsHandlers() {
  document.getElementById('btnRefreshMetrics').addEventListener('click', function () {
    refreshMetricsTab();
  });
}

// ---------------------------------------------------------------------------
// Promise.prototype.finally polyfill (for older WebViews)
// ---------------------------------------------------------------------------
if (typeof Promise.prototype.finally !== 'function') {
  Promise.prototype.finally = function (callback) {
    var P = this.constructor;
    return this.then(
      function (value) {
        return P.resolve(callback()).then(function () { return value; });
      },
      function (reason) {
        return P.resolve(callback()).then(function () { throw reason; });
      }
    );
  };
}

// ---------------------------------------------------------------------------
// Initialize Application
// ---------------------------------------------------------------------------

function init() {
  initNavigation();
  initCategoryHandlers();
  initProductHandlers();
  initAvailabilityHandlers();
  initOrderHandlers();
  initMetricsHandlers();

  // Load initial tab data
  switchTab('products');
}

// Start the app once the DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
