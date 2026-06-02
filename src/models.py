"""
SQLAlchemy ORM models (data layer).

Maps the 3NF schema: categories → products ← price_logs → stores.
Raw price_total and quantity are stored; normalized unit price is computed in Python.
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Real,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM tables."""


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("category_name", name="uq_categories_name"),)

    category_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_name: Mapped[str] = mapped_column(String(128), nullable=False)

    products: Mapped[list[Product]] = relationship(back_populates="category")


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (UniqueConstraint("store_name", name="uq_stores_name"),)

    store_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_name: Mapped[str] = mapped_column(String(128), nullable=False)

    price_logs: Mapped[list[PriceLog]] = relationship(back_populates="store")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("product_name", name="uq_products_name"),
    )

    product_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_name: Mapped[str] = mapped_column(String(256), nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.category_id", ondelete="RESTRICT"),
        nullable=False,
    )

    category: Mapped[Category] = relationship(back_populates="products")
    price_logs: Mapped[list[PriceLog]] = relationship(back_populates="product")


class PriceLog(Base):
    __tablename__ = "price_logs"
    __table_args__ = (
        CheckConstraint("price_total > 0", name="ck_price_logs_price_positive"),
        CheckConstraint("quantity > 0", name="ck_price_logs_qty_positive"),
        CheckConstraint(
            "unit_type IN ('kg', 'g', 'l', 'ml', 'unit')",
            name="ck_price_logs_unit_type",
        ),
        Index("idx_price_date", "date_recorded"),
        Index("idx_product_store", "product_id", "store_id"),
    )

    log_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id", ondelete="RESTRICT"),
        nullable=False,
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.store_id", ondelete="RESTRICT"),
        nullable=False,
    )
    price_total: Mapped[float] = mapped_column(Real, nullable=False)
    quantity: Mapped[float] = mapped_column(Real, nullable=False)
    unit_type: Mapped[str] = mapped_column(String(16), nullable=False)
    date_recorded: Mapped[str] = mapped_column(Date, nullable=False)

    product: Mapped[Product] = relationship(back_populates="price_logs")
    store: Mapped[Store] = relationship(back_populates="price_logs")
