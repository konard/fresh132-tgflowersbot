from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# --- Cart Schemas ---


class CartItemCreate(BaseModel):
    product_id: int
    product_name: str
    product_price: float
    quantity: int = 1


class CartItemUpdate(BaseModel):
    quantity: int


class CartItemResponse(BaseModel):
    id: int
    cart_id: int
    product_id: int
    product_name: str
    product_price: float
    quantity: int

    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    items: list[CartItemResponse] = []

    model_config = {"from_attributes": True}


# --- Order Schemas ---


class OrderItemCreate(BaseModel):
    product_id: int
    product_name: str
    product_price: float
    quantity: int = 1


class OrderCreate(BaseModel):
    user_id: int
    delivery_type: str = "pickup"
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pickup_time: Optional[str] = None
    store_id: Optional[int] = None
    items: list[OrderItemCreate] = []


class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    product_id: int
    product_name: str
    product_price: float
    quantity: int

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: str


class OrderResponse(BaseModel):
    id: int
    user_id: int
    status: str
    delivery_type: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pickup_time: Optional[str] = None
    store_id: Optional[int] = None
    total_amount: float
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []

    model_config = {"from_attributes": True}
