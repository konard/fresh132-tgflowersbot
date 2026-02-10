"""Tests for the /products/ router."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models import Category, Product, ProductAvailability, Store
from tests.conftest import fake_kafka

pytestmark = pytest.mark.asyncio(loop_scope="function")


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------
class TestListProducts:
    async def test_list_products_empty(self, client: AsyncClient) -> None:
        """An empty database should return an empty list."""
        resp = await client.get("/products/")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_products_with_data(
        self, client: AsyncClient, sample_product: Product
    ) -> None:
        """When a product exists the list endpoint should return it."""
        resp = await client.get("/products/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == sample_product.name

    async def test_list_products_filter_by_category(
        self, client: AsyncClient, sample_product: Product
    ) -> None:
        """Filtering by category_id should return only matching products."""
        # Should find the product
        resp = await client.get(
            "/products/", params={"category_id": sample_product.category_id}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_product.id

    async def test_list_products_filter_by_category_no_match(
        self, client: AsyncClient, sample_product: Product
    ) -> None:
        """Filtering by a non-existent category should return an empty list."""
        resp = await client.get("/products/", params={"category_id": 99999})
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------
class TestCreateProduct:
    async def test_create_product(
        self, client: AsyncClient, sample_category: Category
    ) -> None:
        """POST /products/ should create a product, return 201, and send a Kafka event."""
        fake_kafka.clear()
        payload = {
            "name": "White Lily",
            "description": "Elegant white lily",
            "price": 15.50,
            "image_url": "https://example.com/lily.jpg",
            "category_id": sample_category.id,
        }
        resp = await client.post("/products/", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "White Lily"
        assert body["price"] == 15.50
        assert body["category_id"] == sample_category.id
        assert "id" in body
        assert "created_at" in body
        assert "updated_at" in body

        # Verify Kafka event was recorded
        assert len(fake_kafka.events) == 1
        evt = fake_kafka.events[0]
        assert evt["topic"] == "catalog_events"
        assert evt["data"]["event"] == "product_created"
        assert evt["data"]["product_id"] == body["id"]


# ---------------------------------------------------------------------------
# GET by id
# ---------------------------------------------------------------------------
class TestGetProduct:
    async def test_get_product_found(
        self, client: AsyncClient, sample_product: Product
    ) -> None:
        """GET /products/{id} should return the product and fire a view event."""
        fake_kafka.clear()
        resp = await client.get(f"/products/{sample_product.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == sample_product.id
        assert body["name"] == sample_product.name

        # Verify Kafka view event
        assert len(fake_kafka.events) == 1
        evt = fake_kafka.events[0]
        assert evt["topic"] == "product_views"
        assert evt["data"]["event"] == "product_view"

    async def test_get_product_not_found(self, client: AsyncClient) -> None:
        """GET /products/{id} should return 404 for a missing product."""
        resp = await client.get("/products/99999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Product not found"


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------
class TestUpdateProduct:
    async def test_update_product(
        self, client: AsyncClient, sample_product: Product
    ) -> None:
        """PUT /products/{id} should update the product and send a Kafka event."""
        fake_kafka.clear()
        payload = {"name": "Crimson Rose Bouquet", "price": 34.99}
        resp = await client.put(f"/products/{sample_product.id}", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Crimson Rose Bouquet"
        assert body["price"] == 34.99

        # Verify Kafka update event
        assert len(fake_kafka.events) == 1
        evt = fake_kafka.events[0]
        assert evt["topic"] == "catalog_events"
        assert evt["data"]["event"] == "product_updated"

    async def test_update_product_not_found(self, client: AsyncClient) -> None:
        """PUT /products/{id} should return 404 for a missing product."""
        resp = await client.put("/products/99999", json={"name": "Ghost"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------
class TestDeleteProduct:
    async def test_delete_product(
        self, client: AsyncClient, sample_product: Product
    ) -> None:
        """DELETE /products/{id} should remove the product and send a Kafka event."""
        fake_kafka.clear()
        resp = await client.delete(f"/products/{sample_product.id}")
        assert resp.status_code == 204

        # Verify Kafka delete event
        assert len(fake_kafka.events) == 1
        evt = fake_kafka.events[0]
        assert evt["topic"] == "catalog_events"
        assert evt["data"]["event"] == "product_deleted"

        # Verify it's gone
        resp = await client.get(f"/products/{sample_product.id}")
        assert resp.status_code == 404

    async def test_delete_product_not_found(self, client: AsyncClient) -> None:
        """DELETE /products/{id} should return 404 for a missing product."""
        resp = await client.delete("/products/99999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# AVAILABILITY
# ---------------------------------------------------------------------------
class TestProductAvailability:
    async def test_get_product_availability_empty(
        self, client: AsyncClient, sample_product: Product
    ) -> None:
        """Availability for a product with no stock records should be empty."""
        resp = await client.get(f"/products/{sample_product.id}/availability")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_product_availability_with_data(
        self,
        client: AsyncClient,
        sample_product: Product,
        sample_store: Store,
        sample_availability: ProductAvailability,
    ) -> None:
        """Availability should include the store details."""
        resp = await client.get(f"/products/{sample_product.id}/availability")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        item = data[0]
        assert item["product_id"] == sample_product.id
        assert item["store_id"] == sample_store.id
        assert item["quantity"] == 10
        # Nested store object
        assert item["store"]["name"] == sample_store.name

    async def test_get_product_availability_not_found(
        self, client: AsyncClient
    ) -> None:
        """Availability for a non-existent product should return 404."""
        resp = await client.get("/products/99999/availability")
        assert resp.status_code == 404
