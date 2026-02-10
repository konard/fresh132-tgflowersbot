from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import OrderMetric, PopularProduct
from app.schemas import (
    DashboardMetrics,
    OrderMetricResponse,
    PopularProductResponse,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard(session: AsyncSession = Depends(get_session)):
    """Return aggregated dashboard metrics."""
    # Total orders and revenue
    result = await session.execute(
        select(
            func.count(OrderMetric.id),
            func.coalesce(func.sum(OrderMetric.total_amount), 0.0),
        )
    )
    row = result.one()
    total_orders = row[0]
    total_revenue = float(row[1])
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0

    # Orders today
    today_start = datetime.combine(date.today(), time.min)
    result = await session.execute(
        select(func.count(OrderMetric.id)).where(
            OrderMetric.created_at >= today_start
        )
    )
    orders_today = result.scalar_one()

    # Popular by views (top 10)
    result = await session.execute(
        select(PopularProduct)
        .order_by(PopularProduct.view_count.desc())
        .limit(10)
    )
    popular_by_views = [
        PopularProductResponse.model_validate(p) for p in result.scalars().all()
    ]

    # Popular by orders (top 10)
    result = await session.execute(
        select(PopularProduct)
        .order_by(PopularProduct.order_count.desc())
        .limit(10)
    )
    popular_by_orders = [
        PopularProductResponse.model_validate(p) for p in result.scalars().all()
    ]

    return DashboardMetrics(
        total_orders=total_orders,
        total_revenue=total_revenue,
        avg_order_value=round(avg_order_value, 2),
        orders_today=orders_today,
        popular_by_views=popular_by_views,
        popular_by_orders=popular_by_orders,
    )


@router.get("/popular/views", response_model=list[PopularProductResponse])
async def get_popular_by_views(session: AsyncSession = Depends(get_session)):
    """Return top 10 products by view count."""
    result = await session.execute(
        select(PopularProduct)
        .order_by(PopularProduct.view_count.desc())
        .limit(10)
    )
    return [PopularProductResponse.model_validate(p) for p in result.scalars().all()]


@router.get("/popular/orders", response_model=list[PopularProductResponse])
async def get_popular_by_orders(session: AsyncSession = Depends(get_session)):
    """Return top 10 products by order count."""
    result = await session.execute(
        select(PopularProduct)
        .order_by(PopularProduct.order_count.desc())
        .limit(10)
    )
    return [PopularProductResponse.model_validate(p) for p in result.scalars().all()]


@router.get("/orders", response_model=list[OrderMetricResponse])
async def get_order_metrics(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    session: AsyncSession = Depends(get_session),
):
    """Return order metrics optionally filtered by date range."""
    query = select(OrderMetric).order_by(OrderMetric.created_at.desc())

    if from_date is not None:
        from_datetime = datetime.combine(from_date, time.min)
        query = query.where(OrderMetric.created_at >= from_datetime)

    if to_date is not None:
        to_datetime = datetime.combine(to_date, time.max)
        query = query.where(OrderMetric.created_at <= to_datetime)

    result = await session.execute(query)
    return [OrderMetricResponse.model_validate(o) for o in result.scalars().all()]
