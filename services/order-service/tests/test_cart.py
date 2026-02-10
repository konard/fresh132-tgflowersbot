"""Tests for the cart router (``/cart`` endpoints)."""

from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_ITEM = {
    "product_id": 101,
    "product_name": "Red Roses Bouquet",
    "product_price": 29.99,
    "quantity": 1,
}

SAMPLE_ITEM_2 = {
    "product_id": 202,
    "product_name": "White Tulips",
    "product_price": 14.50,
    "quantity": 3,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_get_cart_creates_empty_cart(client: AsyncClient):
    """GET /cart/{user_id} should create and return an empty cart for a new user."""
    response = await client.get("/cart/1001")
    assert response.status_code == 200

    data = response.json()
    assert data["user_id"] == 1001
    assert data["items"] == []
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


async def test_add_item_to_cart(client: AsyncClient):
    """POST /cart/{user_id}/items should add a product to the cart."""
    response = await client.post("/cart/1001/items", json=SAMPLE_ITEM)
    assert response.status_code == 201

    data = response.json()
    assert data["user_id"] == 1001
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["product_id"] == SAMPLE_ITEM["product_id"]
    assert item["product_name"] == SAMPLE_ITEM["product_name"]
    assert item["product_price"] == SAMPLE_ITEM["product_price"]
    assert item["quantity"] == SAMPLE_ITEM["quantity"]


async def test_add_same_product_increments_quantity(client: AsyncClient):
    """Adding the same product_id twice should increment the quantity."""
    await client.post("/cart/1001/items", json=SAMPLE_ITEM)

    # Add the same product again with quantity 2
    second_add = {**SAMPLE_ITEM, "quantity": 2}
    response = await client.post("/cart/1001/items", json=second_add)
    assert response.status_code == 201

    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 3  # 1 + 2


async def test_add_multiple_different_products(client: AsyncClient):
    """Adding two different products should result in two cart items."""
    await client.post("/cart/1001/items", json=SAMPLE_ITEM)
    response = await client.post("/cart/1001/items", json=SAMPLE_ITEM_2)
    assert response.status_code == 201

    data = response.json()
    assert len(data["items"]) == 2

    product_ids = {item["product_id"] for item in data["items"]}
    assert product_ids == {101, 202}


async def test_update_item_quantity(client: AsyncClient):
    """PUT /cart/{user_id}/items/{item_id} should update the quantity."""
    # First add an item
    add_resp = await client.post("/cart/1001/items", json=SAMPLE_ITEM)
    item_id = add_resp.json()["items"][0]["id"]

    # Update quantity
    response = await client.put(
        f"/cart/1001/items/{item_id}",
        json={"quantity": 5},
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 5


async def test_update_item_quantity_to_zero_removes_item(client: AsyncClient):
    """Setting quantity to 0 should remove the item from the cart."""
    add_resp = await client.post("/cart/1001/items", json=SAMPLE_ITEM)
    item_id = add_resp.json()["items"][0]["id"]

    response = await client.put(
        f"/cart/1001/items/{item_id}",
        json={"quantity": 0},
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_update_nonexistent_item_returns_404(client: AsyncClient):
    """Updating a cart item that does not exist should return 404."""
    # Ensure the cart exists
    await client.get("/cart/1001")

    response = await client.put(
        "/cart/1001/items/9999",
        json={"quantity": 2},
    )
    assert response.status_code == 404


async def test_remove_item(client: AsyncClient):
    """DELETE /cart/{user_id}/items/{item_id} should remove the item."""
    add_resp = await client.post("/cart/1001/items", json=SAMPLE_ITEM)
    item_id = add_resp.json()["items"][0]["id"]

    response = await client.delete(f"/cart/1001/items/{item_id}")
    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_remove_nonexistent_item_returns_404(client: AsyncClient):
    """Removing a cart item that does not exist should return 404."""
    await client.get("/cart/1001")

    response = await client.delete("/cart/1001/items/9999")
    assert response.status_code == 404


async def test_clear_cart(client: AsyncClient):
    """DELETE /cart/{user_id} should remove all items from the cart."""
    # Add two items
    await client.post("/cart/1001/items", json=SAMPLE_ITEM)
    await client.post("/cart/1001/items", json=SAMPLE_ITEM_2)

    # Verify items were added
    cart_resp = await client.get("/cart/1001")
    assert len(cart_resp.json()["items"]) == 2

    # Clear
    response = await client.delete("/cart/1001")
    assert response.status_code == 200

    data = response.json()
    assert data["items"] == []
    # The cart itself should still exist
    assert data["user_id"] == 1001
