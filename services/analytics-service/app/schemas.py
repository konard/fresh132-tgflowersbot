from datetime import datetime

from pydantic import BaseModel


class PopularProductResponse(BaseModel):
    product_id: int
    product_name: str
    view_count: int
    order_count: int

    model_config = {"from_attributes": True}


class OrderMetricResponse(BaseModel):
    id: int
    order_id: int
    user_id: int
    total_amount: float
    items_count: int
    delivery_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardMetrics(BaseModel):
    total_orders: int
    total_revenue: float
    avg_order_value: float
    orders_today: int
    popular_by_views: list[PopularProductResponse]
    popular_by_orders: list[PopularProductResponse]
