import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Product, ProductAvailability, Store
from ..schemas import (
    ProductAvailabilityCreate,
    ProductAvailabilityResponse,
    StoreCreate,
    StoreResponse,
    StoreUpdate,
)

router = APIRouter(prefix="/stores", tags=["stores"])


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in kilometres between two points."""
    R = 6371.0  # Earth radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@router.get("/", response_model=list[StoreResponse])
async def list_stores(db: AsyncSession = Depends(get_db)):
    """Return all stores."""
    result = await db.execute(select(Store).order_by(Store.id))
    stores = result.scalars().all()
    return stores


@router.get("/nearby", response_model=list[StoreResponse])
async def get_nearby_stores(
    lat: float = Query(..., description="User latitude"),
    lon: float = Query(..., description="User longitude"),
    radius_km: float = Query(default=10.0, description="Search radius in km"),
    db: AsyncSession = Depends(get_db),
):
    """Return stores within *radius_km* of the given coordinates, sorted by distance."""
    result = await db.execute(select(Store))
    all_stores = result.scalars().all()

    nearby: list[tuple[float, Store]] = []
    for store in all_stores:
        dist = _haversine_distance(lat, lon, store.latitude, store.longitude)
        if dist <= radius_km:
            nearby.append((dist, store))

    nearby.sort(key=lambda t: t[0])
    return [store for _, store in nearby]


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(store_id: int, db: AsyncSession = Depends(get_db)):
    """Return a single store by ID."""
    store = await db.get(Store, store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )
    return store


@router.post("/", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def create_store(payload: StoreCreate, db: AsyncSession = Depends(get_db)):
    """Create a new store."""
    store = Store(**payload.model_dump())
    db.add(store)
    await db.flush()
    await db.refresh(store)
    return store


@router.put("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: int,
    payload: StoreUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing store."""
    store = await db.get(Store, store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(store, field, value)
    await db.flush()
    await db.refresh(store)
    return store


@router.post(
    "/{store_id}/products/{product_id}/availability",
    response_model=ProductAvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def set_product_availability(
    store_id: int,
    product_id: int,
    payload: ProductAvailabilityCreate,
    db: AsyncSession = Depends(get_db),
):
    """Set (or update) product availability for a given store.

    If an availability record already exists for the (product, store) pair it
    will be updated; otherwise a new one is created.
    """
    # Validate that both the store and product exist
    store = await db.get(Store, store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Check for existing record
    stmt = select(ProductAvailability).where(
        ProductAvailability.store_id == store_id,
        ProductAvailability.product_id == product_id,
    )
    result = await db.execute(stmt)
    availability = result.scalar_one_or_none()

    if availability is not None:
        availability.quantity = payload.quantity
    else:
        availability = ProductAvailability(
            product_id=product_id,
            store_id=store_id,
            quantity=payload.quantity,
        )
        db.add(availability)

    await db.flush()
    await db.refresh(availability)
    return availability
