from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProductView(Base):
    __tablename__ = "product_views"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class OrderMetric(Base):
    __tablename__ = "order_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    items_count: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class PopularProduct(Base):
    __tablename__ = "popular_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    product_name: Mapped[str] = mapped_column(String, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    order_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
