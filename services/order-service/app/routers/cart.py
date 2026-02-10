from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Cart, CartItem
from app.schemas import CartItemCreate, CartItemUpdate, CartResponse

router = APIRouter(prefix="/cart", tags=["cart"])


async def _get_or_create_cart(user_id: int, session: AsyncSession) -> Cart:
    """Return the cart for *user_id*, creating one if it does not exist."""
    result = await session.execute(
        select(Cart).where(Cart.user_id == user_id).options(selectinload(Cart.items))
    )
    cart = result.scalar_one_or_none()
    if cart is None:
        cart = Cart(user_id=user_id)
        session.add(cart)
        await session.commit()
        await session.refresh(cart, attribute_names=["items"])
    return cart


@router.get("/{user_id}", response_model=CartResponse)
async def get_cart(user_id: int, session: AsyncSession = Depends(get_session)):
    """Get the current cart for a user (creates an empty one if none exists)."""
    cart = await _get_or_create_cart(user_id, session)
    return cart


@router.post("/{user_id}/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def add_item_to_cart(
    user_id: int,
    item: CartItemCreate,
    session: AsyncSession = Depends(get_session),
):
    """Add a product to the user's cart.

    If the same *product_id* already exists in the cart the quantity is incremented.
    """
    cart = await _get_or_create_cart(user_id, session)

    # Check if the product is already in the cart
    existing_item: CartItem | None = None
    for ci in cart.items:
        if ci.product_id == item.product_id:
            existing_item = ci
            break

    if existing_item is not None:
        existing_item.quantity += item.quantity
    else:
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=item.product_id,
            product_name=item.product_name,
            product_price=item.product_price,
            quantity=item.quantity,
        )
        session.add(cart_item)

    await session.commit()
    await session.refresh(cart, attribute_names=["items"])
    return cart


@router.put("/{user_id}/items/{item_id}", response_model=CartResponse)
async def update_cart_item(
    user_id: int,
    item_id: int,
    update: CartItemUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update the quantity of a specific cart item."""
    cart = await _get_or_create_cart(user_id, session)

    result = await session.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    )
    cart_item = result.scalar_one_or_none()
    if cart_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    if update.quantity <= 0:
        await session.delete(cart_item)
    else:
        cart_item.quantity = update.quantity

    await session.commit()
    await session.refresh(cart, attribute_names=["items"])
    return cart


@router.delete("/{user_id}/items/{item_id}", response_model=CartResponse)
async def remove_cart_item(
    user_id: int,
    item_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Remove a single item from the user's cart."""
    cart = await _get_or_create_cart(user_id, session)

    result = await session.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    )
    cart_item = result.scalar_one_or_none()
    if cart_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    await session.delete(cart_item)
    await session.commit()
    await session.refresh(cart, attribute_names=["items"])
    return cart


@router.delete("/{user_id}", response_model=CartResponse)
async def clear_cart(user_id: int, session: AsyncSession = Depends(get_session)):
    """Remove all items from the user's cart."""
    cart = await _get_or_create_cart(user_id, session)

    for item in list(cart.items):
        await session.delete(item)

    await session.commit()
    await session.refresh(cart, attribute_names=["items"])
    return cart
