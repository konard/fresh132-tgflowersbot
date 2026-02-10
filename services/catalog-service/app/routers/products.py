import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..kafka_producer import kafka_producer
from ..models import Product, ProductAvailability
from ..schemas import (
    ProductAvailabilityDetailResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=list[ProductResponse])
async def list_products(
    category_id: int | None = Query(default=None, description="Filter by category"),
    db: AsyncSession = Depends(get_db),
):
    """Return all products, optionally filtered by *category_id*."""
    stmt = select(Product).order_by(Product.id)
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    result = await db.execute(stmt)
    products = result.scalars().all()
    return products


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Return a single product by ID and publish a view event to Kafka."""
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Fire-and-forget: publish a product_view event (non-blocking)
    await kafka_producer.send_event(
        "product_views",
        {
            "event": "product_view",
            "product_id": product.id,
            "product_name": product.name,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        },
    )

    return product


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new product."""
    product = Product(**payload.model_dump())
    db.add(product)
    await db.flush()
    await db.refresh(product)

    await kafka_producer.send_event(
        "catalog_events",
        {
            "event": "product_created",
            "product_id": product.id,
            "name": product.name,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        },
    )

    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing product."""
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    await db.flush()
    await db.refresh(product)

    await kafka_producer.send_event(
        "catalog_events",
        {
            "event": "product_updated",
            "product_id": product.id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        },
    )

    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a product."""
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    deleted_id = product.id
    await db.delete(product)
    await db.flush()

    await kafka_producer.send_event(
        "catalog_events",
        {
            "event": "product_deleted",
            "product_id": deleted_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        },
    )

    return None


@router.get(
    "/{product_id}/availability",
    response_model=list[ProductAvailabilityDetailResponse],
)
async def get_product_availability(
    product_id: int, db: AsyncSession = Depends(get_db)
):
    """Return availability of a product across all stores."""
    # Ensure the product exists
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    stmt = (
        select(ProductAvailability)
        .where(ProductAvailability.product_id == product_id)
        .options(selectinload(ProductAvailability.store))
    )
    result = await db.execute(stmt)
    availability = result.scalars().all()
    return availability
