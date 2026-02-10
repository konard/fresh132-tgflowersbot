"""Tests for the /categories/ router."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models import Category

pytestmark = pytest.mark.asyncio(loop_scope="function")


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------
class TestListCategories:
    async def test_list_categories_empty(self, client: AsyncClient) -> None:
        """An empty database should return an empty list."""
        resp = await client.get("/categories/")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_categories_with_data(
        self, client: AsyncClient, sample_category: Category
    ) -> None:
        """When a category exists the list endpoint should return it."""
        resp = await client.get("/categories/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == sample_category.name
        assert data[0]["id"] == sample_category.id


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------
class TestCreateCategory:
    async def test_create_category(self, client: AsyncClient) -> None:
        """POST /categories/ should create a category and return 201."""
        payload = {"name": "Tulips", "description": "Colourful tulips"}
        resp = await client.post("/categories/", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Tulips"
        assert body["description"] == "Colourful tulips"
        assert "id" in body
        assert "created_at" in body

    async def test_create_category_minimal(self, client: AsyncClient) -> None:
        """Creating a category without an optional description should work."""
        payload = {"name": "Orchids"}
        resp = await client.post("/categories/", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Orchids"
        assert body["description"] is None


# ---------------------------------------------------------------------------
# GET by id
# ---------------------------------------------------------------------------
class TestGetCategory:
    async def test_get_category_found(
        self, client: AsyncClient, sample_category: Category
    ) -> None:
        """GET /categories/{id} should return the matching category."""
        resp = await client.get(f"/categories/{sample_category.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == sample_category.id
        assert body["name"] == sample_category.name

    async def test_get_category_not_found(self, client: AsyncClient) -> None:
        """GET /categories/{id} should return 404 for a missing category."""
        resp = await client.get("/categories/99999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Category not found"


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------
class TestUpdateCategory:
    async def test_update_category(
        self, client: AsyncClient, sample_category: Category
    ) -> None:
        """PUT /categories/{id} should update and return the category."""
        payload = {"name": "Premium Roses", "description": "Long-stemmed premium roses"}
        resp = await client.put(f"/categories/{sample_category.id}", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Premium Roses"
        assert body["description"] == "Long-stemmed premium roses"

    async def test_update_category_partial(
        self, client: AsyncClient, sample_category: Category
    ) -> None:
        """A partial update should only change the provided fields."""
        payload = {"name": "Garden Roses"}
        resp = await client.put(f"/categories/{sample_category.id}", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Garden Roses"
        # description should remain unchanged
        assert body["description"] == sample_category.description

    async def test_update_category_not_found(self, client: AsyncClient) -> None:
        """PUT /categories/{id} should return 404 for a missing category."""
        resp = await client.put("/categories/99999", json={"name": "Ghost"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------
class TestDeleteCategory:
    async def test_delete_category(
        self, client: AsyncClient, sample_category: Category
    ) -> None:
        """DELETE /categories/{id} should remove the category and return 204."""
        resp = await client.delete(f"/categories/{sample_category.id}")
        assert resp.status_code == 204

        # Verify it's gone
        resp = await client.get(f"/categories/{sample_category.id}")
        assert resp.status_code == 404

    async def test_delete_category_not_found(self, client: AsyncClient) -> None:
        """DELETE /categories/{id} should return 404 for a missing category."""
        resp = await client.delete("/categories/99999")
        assert resp.status_code == 404
