"""Tests for the /stores/ router."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models import Category, Product, ProductAvailability, Store

pytestmark = pytest.mark.asyncio(loop_scope="function")


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------
class TestListStores:
    async def test_list_stores_empty(self, client: AsyncClient) -> None:
        """An empty database should return an empty list."""
        resp = await client.get("/stores/")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_stores_with_data(
        self, client: AsyncClient, sample_store: Store
    ) -> None:
        """When a store exists the list endpoint should return it."""
        resp = await client.get("/stores/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == sample_store.name
        assert data[0]["id"] == sample_store.id


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------
class TestCreateStore:
    async def test_create_store(self, client: AsyncClient) -> None:
        """POST /stores/ should create a store and return 201."""
        payload = {
            "name": "Uptown Blossoms",
            "address": "456 Park Ave",
            "latitude": 40.7580,
            "longitude": -73.9855,
            "phone": "+1-555-0200",
        }
        resp = await client.post("/stores/", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Uptown Blossoms"
        assert body["address"] == "456 Park Ave"
        assert body["latitude"] == pytest.approx(40.7580)
        assert body["longitude"] == pytest.approx(-73.9855)
        assert "id" in body

    async def test_create_store_minimal(self, client: AsyncClient) -> None:
        """Creating a store without optional fields should work."""
        payload = {
            "name": "Tiny Shop",
            "latitude": 51.5074,
            "longitude": -0.1278,
        }
        resp = await client.post("/stores/", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Tiny Shop"
        assert body["address"] is None
        assert body["phone"] is None


# ---------------------------------------------------------------------------
# GET by id
# ---------------------------------------------------------------------------
class TestGetStore:
    async def test_get_store_found(
        self, client: AsyncClient, sample_store: Store
    ) -> None:
        """GET /stores/{id} should return the matching store."""
        resp = await client.get(f"/stores/{sample_store.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == sample_store.id
        assert body["name"] == sample_store.name

    async def test_get_store_not_found(self, client: AsyncClient) -> None:
        """GET /stores/{id} should return 404 for a missing store."""
        resp = await client.get("/stores/99999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Store not found"


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------
class TestUpdateStore:
    async def test_update_store(
        self, client: AsyncClient, sample_store: Store
    ) -> None:
        """PUT /stores/{id} should update and return the store."""
        payload = {"name": "Downtown Flowers Deluxe", "phone": "+1-555-9999"}
        resp = await client.put(f"/stores/{sample_store.id}", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Downtown Flowers Deluxe"
        assert body["phone"] == "+1-555-9999"
        # Unchanged fields should persist
        assert body["latitude"] == pytest.approx(sample_store.latitude)

    async def test_update_store_not_found(self, client: AsyncClient) -> None:
        """PUT /stores/{id} should return 404 for a missing store."""
        resp = await client.put("/stores/99999", json={"name": "Ghost"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# NEARBY
# ---------------------------------------------------------------------------
class TestNearbyStores:
    async def test_nearby_stores_found(
        self, client: AsyncClient, sample_store: Store
    ) -> None:
        """Stores within the radius should be returned."""
        resp = await client.get(
            "/stores/nearby",
            params={
                "lat": sample_store.latitude,
                "lon": sample_store.longitude,
                "radius_km": 1.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_store.id

    async def test_nearby_stores_none_in_range(
        self, client: AsyncClient, sample_store: Store
    ) -> None:
        """A location far away from any store should return an empty list."""
        resp = await client.get(
            "/stores/nearby",
            params={
                "lat": -33.8688,  # Sydney
                "lon": 151.2093,
                "radius_km": 1.0,
            },
        )
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# PRODUCT AVAILABILITY (set via stores router)
# ---------------------------------------------------------------------------
class TestSetProductAvailability:
    async def test_set_availability_new(
        self,
        client: AsyncClient,
        sample_store: Store,
        sample_product: Product,
    ) -> None:
        """POST .../availability should create a new availability record."""
        url = f"/stores/{sample_store.id}/products/{sample_product.id}/availability"
        resp = await client.post(url, json={"quantity": 25})
        assert resp.status_code == 201
        body = resp.json()
        assert body["store_id"] == sample_store.id
        assert body["product_id"] == sample_product.id
        assert body["quantity"] == 25

    async def test_set_availability_update_existing(
        self,
        client: AsyncClient,
        sample_store: Store,
        sample_product: Product,
        sample_availability: ProductAvailability,
    ) -> None:
        """Posting again for the same (store, product) should update the quantity."""
        url = f"/stores/{sample_store.id}/products/{sample_product.id}/availability"
        resp = await client.post(url, json={"quantity": 42})
        assert resp.status_code == 201
        body = resp.json()
        assert body["quantity"] == 42
        # Should be the same record (same id)
        assert body["id"] == sample_availability.id

    async def test_set_availability_store_not_found(
        self, client: AsyncClient, sample_product: Product
    ) -> None:
        """Setting availability for a non-existent store should return 404."""
        url = f"/stores/99999/products/{sample_product.id}/availability"
        resp = await client.post(url, json={"quantity": 5})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Store not found"

    async def test_set_availability_product_not_found(
        self, client: AsyncClient, sample_store: Store
    ) -> None:
        """Setting availability for a non-existent product should return 404."""
        url = f"/stores/{sample_store.id}/products/99999/availability"
        resp = await client.post(url, json={"quantity": 5})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Product not found"
