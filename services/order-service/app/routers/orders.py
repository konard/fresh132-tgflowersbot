from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.kafka_producer import send_event
from app.models import Cart, Order, OrderItem
from app.schemas import OrderCreate, OrderItemCreate, OrderResponse, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_in: OrderCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new order.

    If *order_in.items* is empty the items are taken from the user's cart.
    After a successful order the cart is cleared.
    """
    items_data = order_in.items

    # If no explicit items provided, pull from the user's cart
    if not items_data:
        result = await session.execute(
            select(Cart)
            .where(Cart.user_id == order_in.user_id)
            .options(selectinload(Cart.items))
        )
        cart = result.scalar_one_or_none()
        if cart is None or not cart.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No items provided and user cart is empty",
            )
        items_data = [
            OrderItemCreate(
                product_id=ci.product_id,
                product_name=ci.product_name,
                product_price=ci.product_price,
                quantity=ci.quantity,
            )
            for ci in cart.items
        ]

    # Calculate total
    total_amount = sum(item.product_price * item.quantity for item in items_data)

    order = Order(
        user_id=order_in.user_id,
        delivery_type=order_in.delivery_type,
        address=order_in.address,
        latitude=order_in.latitude,
        longitude=order_in.longitude,
        pickup_time=order_in.pickup_time,
        store_id=order_in.store_id,
        total_amount=total_amount,
    )
    session.add(order)
    await session.flush()  # get order.id before adding items

    order_items: list[OrderItem] = []
    for item in items_data:
        oi = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            product_name=item.product_name,
            product_price=item.product_price,
            quantity=item.quantity,
        )
        session.add(oi)
        order_items.append(oi)

    # Clear user cart
    result = await session.execute(
        select(Cart)
        .where(Cart.user_id == order_in.user_id)
        .options(selectinload(Cart.items))
    )
    cart = result.scalar_one_or_none()
    if cart is not None:
        for ci in list(cart.items):
            await session.delete(ci)

    await session.commit()
    await session.refresh(order, attribute_names=["items"])

    # Publish Kafka event
    event = {
        "event": "order_created",
        "order_id": order.id,
        "user_id": order.user_id,
        "status": order.status,
        "delivery_type": order.delivery_type,
        "address": order.address,
        "latitude": order.latitude,
        "longitude": order.longitude,
        "pickup_time": order.pickup_time,
        "store_id": order.store_id,
        "total_amount": order.total_amount,
        "items": [
            {
                "product_id": oi.product_id,
                "product_name": oi.product_name,
                "product_price": oi.product_price,
                "quantity": oi.quantity,
            }
            for oi in order.items
        ],
        "created_at": order.created_at,
    }
    await send_event("order_events", event)

    return order


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, session: AsyncSession = Depends(get_session)):
    """Get a single order by ID."""
    result = await session.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.get("/user/{user_id}", response_model=list[OrderResponse])
async def get_user_orders(user_id: int, session: AsyncSession = Depends(get_session)):
    """Get all orders for a specific user."""
    result = await session.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    return orders


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update the status of an order."""
    result = await session.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order.status = status_update.status
    await session.commit()
    await session.refresh(order, attribute_names=["items"])

    # Publish status update event
    event = {
        "event": "order_status_updated",
        "order_id": order.id,
        "user_id": order.user_id,
        "status": order.status,
        "updated_at": order.updated_at,
    }
    await send_event("order_events", event)

    return order


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    skip: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    """List all orders (admin endpoint). Supports pagination."""
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    orders = result.scalars().all()
    return orders
