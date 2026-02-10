import datetime

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------
class CategoryCreate(BaseModel):
    name: str
    description: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    created_at: datetime.datetime


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------
class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    price: float
    image_url: str | None = None
    category_id: int


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    image_url: str | None = None
    category_id: int | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    price: float
    image_url: str | None = None
    category_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------
class StoreCreate(BaseModel):
    name: str
    address: str | None = None
    latitude: float
    longitude: float
    phone: str | None = None


class StoreUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    phone: str | None = None


class StoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str | None = None
    latitude: float
    longitude: float
    phone: str | None = None


# ---------------------------------------------------------------------------
# ProductAvailability
# ---------------------------------------------------------------------------
class ProductAvailabilityCreate(BaseModel):
    quantity: int


class ProductAvailabilityUpdate(BaseModel):
    quantity: int


class ProductAvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    store_id: int
    quantity: int


class ProductAvailabilityDetailResponse(BaseModel):
    """Availability response that includes store information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    store_id: int
    quantity: int
    store: StoreResponse
