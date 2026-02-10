"""Tests for the orders router (``/orders`` endpoints)."""

from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_ORDER_ITEMS = [
    {
        "product_id": 101,
        "product_name": "Red Roses Bouquet",
        "product_price": 29.99,
        "quantity": 2,
    },
    {
        "product_id": 202,
        "product_name": "White Tulips",
        "product_price": 14.50,
        "quantity": 1,
    },
]

CART_ITEM = {
    "product_id": 303,
    "product_name": "Sunflower Bunch",
    "product_price": 12.00,
    "quantity": 4,
}


async def _create_order_with_items(client: AsyncClient) -> dict:
    """Helper: create an order with explicit items and return the JSON."""
    payload = {
        "user_id": 2001,
        "delivery_type": "delivery",
        "address": "123 Flower St",
        "items": SAMPLE_ORDER_ITEMS,
    }
    response = await client.post("/orders/", json=payload)
    assert response.status_code == 201
    return response.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_create_order_with_explicit_items(client: AsyncClient):
    """POST /orders/ with items in the body should create the order."""
    data = await _create_order_with_items(client)

    assert data["user_id"] == 2001
    assert data["status"] == "pending"
    assert data["delivery_type"] == "delivery"
    assert data["address"] == "123 Flower St"
    assert len(data["items"]) == 2

    expected_total = 29.99 * 2 + 14.50 * 1  # 74.48
    assert abs(data["total_amount"] - expected_total) < 0.01

    product_ids = {item["product_id"] for item in data["items"]}
    assert product_ids == {101, 202}


async def test_create_order_from_cart(client: AsyncClient):
    """POST /orders/ without items should pull items from the user's cart."""
    # Populate the cart first
    await client.post("/cart/3001/items", json=CART_ITEM)

    # Create order with no explicit items
    payload = {"user_id": 3001}
    response = await client.post("/orders/", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["user_id"] == 3001
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == CART_ITEM["product_id"]
    assert data["items"][0]["quantity"] == CART_ITEM["quantity"]

    expected_total = CART_ITEM["product_price"] * CART_ITEM["quantity"]
    assert abs(data["total_amount"] - expected_total) < 0.01

    # Cart should be cleared after creating the order
    cart_resp = await client.get("/cart/3001")
    assert cart_resp.json()["items"] == []


async def test_create_order_empty_cart_fails(client: AsyncClient):
    """POST /orders/ with no items and an empty cart should return 400."""
    payload = {"user_id": 4001}
    response = await client.post("/orders/", json=payload)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


async def test_get_order_by_id(client: AsyncClient):
    """GET /orders/{order_id} should return the order."""
    created = await _create_order_with_items(client)
    order_id = created["id"]

    response = await client.get(f"/orders/{order_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == order_id
    assert data["user_id"] == 2001
    assert len(data["items"]) == 2


async def test_get_nonexistent_order_returns_404(client: AsyncClient):
    """GET /orders/{order_id} for a missing ID should return 404."""
    response = await client.get("/orders/99999")
    assert response.status_code == 404


async def test_get_user_orders(client: AsyncClient):
    """GET /orders/user/{user_id} should return all orders for that user."""
    # Create two orders for the same user
    for _ in range(2):
        payload = {
            "user_id": 5001,
            "items": SAMPLE_ORDER_ITEMS,
        }
        resp = await client.post("/orders/", json=payload)
        assert resp.status_code == 201

    response = await client.get("/orders/user/5001")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2
    for order in data:
        assert order["user_id"] == 5001


async def test_get_user_orders_empty(client: AsyncClient):
    """GET /orders/user/{user_id} with no orders should return an empty list."""
    response = await client.get("/orders/user/9999")
    assert response.status_code == 200
    assert response.json() == []


async def test_update_order_status(client: AsyncClient):
    """PUT /orders/{order_id}/status should update the order status."""
    created = await _create_order_with_items(client)
    order_id = created["id"]
    assert created["status"] == "pending"

    response = await client.put(
        f"/orders/{order_id}/status",
        json={"status": "confirmed"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "confirmed"


async def test_update_nonexistent_order_status_returns_404(client: AsyncClient):
    """PUT /orders/{order_id}/status for a missing order should return 404."""
    response = await client.put(
        "/orders/99999/status",
        json={"status": "confirmed"},
    )
    assert response.status_code == 404


async def test_list_all_orders(client: AsyncClient):
    """GET /orders/ should list all orders with pagination support."""
    # Create three orders for different users
    for uid in (6001, 6002, 6003):
        payload = {
            "user_id": uid,
            "items": SAMPLE_ORDER_ITEMS,
        }
        resp = await client.post("/orders/", json=payload)
        assert resp.status_code == 201

    response = await client.get("/orders/")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 3


async def test_list_orders_pagination(client: AsyncClient):
    """GET /orders/?skip=&limit= should paginate results."""
    for uid in (7001, 7002, 7003, 7004):
        payload = {
            "user_id": uid,
            "items": SAMPLE_ORDER_ITEMS,
        }
        resp = await client.post("/orders/", json=payload)
        assert resp.status_code == 201

    # Get second page with limit 2
    response = await client.get("/orders/?skip=2&limit=2")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2


async def test_order_clears_cart_after_creation(client: AsyncClient):
    """Creating an order with explicit items should also clear the user's cart."""
    # Add items to cart
    await client.post("/cart/8001/items", json=CART_ITEM)
    cart_resp = await client.get("/cart/8001")
    assert len(cart_resp.json()["items"]) == 1

    # Create order with explicit items (not from cart)
    payload = {
        "user_id": 8001,
        "items": SAMPLE_ORDER_ITEMS,
    }
    resp = await client.post("/orders/", json=payload)
    assert resp.status_code == 201

    # Cart should still be cleared
    cart_resp = await client.get("/cart/8001")
    assert cart_resp.json()["items"] == []
