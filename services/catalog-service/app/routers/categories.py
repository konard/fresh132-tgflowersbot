from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Category
from ..schemas import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Return all categories."""
    result = await db.execute(select(Category).order_by(Category.id))
    categories = result.scalars().all()
    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    """Return a single category by ID."""
    category = await db.get(Category, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return category


@router.post(
    "/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_category(
    payload: CategoryCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new category."""
    category = Category(**payload.model_dump())
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing category."""
    category = await db.get(Category, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    await db.flush()
    await db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a category."""
    category = await db.get(Category, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    await db.delete(category)
    await db.flush()
    return None
