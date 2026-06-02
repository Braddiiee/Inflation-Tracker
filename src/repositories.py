"""
Repository layer — CRUD operations per table.

Each repository accepts a SQLAlchemy Session (injected by caller or via get_session).
Validation runs before writes; IntegrityError is mapped to DatabaseError / ValidationError.
"""

from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from src.exceptions import DatabaseError, NotFoundError, ValidationError
from src.models import Category, PriceLog, Product, Store
from src.validation import (
    normalize_name,
    validate_date_recorded,
    validate_notes,
    validate_positive_number,
    validate_unit_type,
)


def _handle_integrity(exc: IntegrityError, context: str) -> None:
    """Translate SQLite uniqueness/FK failures into domain exceptions."""
    message = str(exc.orig) if exc.orig else str(exc)
    if "UNIQUE" in message.upper():
        raise ValidationError(f"Duplicate entry: {context}") from exc
    if "FOREIGN KEY" in message.upper():
        raise ValidationError(f"Invalid reference: {context}") from exc
    raise DatabaseError(f"Database constraint failed: {context}") from exc


class CategoryRepository:
    """CRUD for the categories lookup table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, category_name: str) -> Category:
        """Insert a category; category_name must be unique (case-sensitive in DB)."""
        name = normalize_name(category_name, "category_name")
        row = Category(category_name=name)
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            _handle_integrity(exc, f"category '{name}'")
        return row

    def get_by_id(self, category_id: int) -> Category:
        """Fetch one category by primary key or raise NotFoundError."""
        row = self._session.get(Category, category_id)
        if row is None:
            raise NotFoundError(f"Category id={category_id} not found.")
        return row

    def get_by_name(self, category_name: str) -> Category | None:
        """Fetch a category by exact name after strip, or None."""
        name = normalize_name(category_name, "category_name")
        return self._session.scalar(
            select(Category).where(Category.category_name == name)
        )

    def get_or_create(self, category_name: str) -> Category:
        """Return existing category or create a new one."""
        existing = self.get_by_name(category_name)
        if existing:
            return existing
        return self.create(category_name)

    def list_all(self) -> list[Category]:
        """Return all categories ordered by name."""
        return list(
            self._session.scalars(
                select(Category).order_by(Category.category_name)
            )
        )

    def update(self, category_id: int, category_name: str) -> Category:
        """Rename a category."""
        row = self.get_by_id(category_id)
        row.category_name = normalize_name(category_name, "category_name")
        try:
            self._session.flush()
        except IntegrityError as exc:
            _handle_integrity(exc, f"category id={category_id}")
        return row

    def delete(self, category_id: int) -> None:
        """Delete a category; fails if products still reference it (RESTRICT)."""
        row = self.get_by_id(category_id)
        try:
            self._session.delete(row)
            self._session.flush()
        except IntegrityError as exc:
            _handle_integrity(
                exc,
                f"cannot delete category id={category_id} (products exist)",
            )


class StoreRepository:
    """CRUD for the stores lookup table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, store_name: str) -> Store:
        """Insert a store with a unique name."""
        name = normalize_name(store_name, "store_name")
        row = Store(store_name=name)
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            _handle_integrity(exc, f"store '{name}'")
        return row

    def get_by_id(self, store_id: int) -> Store:
        """Fetch one store by primary key or raise NotFoundError."""
        row = self._session.get(Store, store_id)
        if row is None:
            raise NotFoundError(f"Store id={store_id} not found.")
        return row

    def get_by_name(self, store_name: str) -> Store | None:
        """Fetch a store by exact name after strip, or None."""
        name = normalize_name(store_name, "store_name")
        return self._session.scalar(select(Store).where(Store.store_name == name))

    def get_or_create(self, store_name: str) -> Store:
        """Return existing store or create a new one."""
        existing = self.get_by_name(store_name)
        if existing:
            return existing
        return self.create(store_name)

    def list_all(self) -> list[Store]:
        """Return all stores ordered by name."""
        return list(
            self._session.scalars(select(Store).order_by(Store.store_name))
        )

    def update(self, store_id: int, store_name: str) -> Store:
        """Rename a store."""
        row = self.get_by_id(store_id)
        row.store_name = normalize_name(store_name, "store_name")
        try:
            self._session.flush()
        except IntegrityError as exc:
            _handle_integrity(exc, f"store id={store_id}")
        return row

    def delete(self, store_id: int) -> None:
        """Delete a store; fails if price_logs still reference it."""
        row = self.get_by_id(store_id)
        try:
            self._session.delete(row)
            self._session.flush()
        except IntegrityError as exc:
            _handle_integrity(
                exc,
                f"cannot delete store id={store_id} (price logs exist)",
            )


class ProductRepository:
    """CRUD for the products master table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, product_name: str, category_id: int) -> Product:
        """Insert a product linked to an existing category."""
        name = normalize_name(product_name, "product_name")
        CategoryRepository(self._session).get_by_id(category_id)
        row = Product(product_name=name, category_id=category_id)
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            _handle_integrity(exc, f"product '{name}'")
        return row

    def get_by_id(self, product_id: int) -> Product:
        """Fetch one product with its category loaded."""
        row = self._session.scalar(
            select(Product)
            .options(joinedload(Product.category))
            .where(Product.product_id == product_id)
        )
        if row is None:
            raise NotFoundError(f"Product id={product_id} not found.")
        return row

    def get_by_name(self, product_name: str) -> Product | None:
        """Fetch a product by exact name after strip, or None."""
        name = normalize_name(product_name, "product_name")
        return self._session.scalar(
            select(Product).where(Product.product_name == name)
        )

    def list_all(self, category_id: int | None = None) -> list[Product]:
        """Return products, optionally filtered by category_id."""
        stmt = select(Product).options(joinedload(Product.category))
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        stmt = stmt.order_by(Product.product_name)
        return list(self._session.scalars(stmt).unique())

    def update(
        self,
        product_id: int,
        *,
        product_name: str | None = None,
        category_id: int | None = None,
    ) -> Product:
        """Update product name and/or category."""
        row = self.get_by_id(product_id)
        if product_name is not None:
            row.product_name = normalize_name(product_name, "product_name")
        if category_id is not None:
            CategoryRepository(self._session).get_by_id(category_id)
            row.category_id = category_id
        try:
            self._session.flush()
        except IntegrityError as exc:
            _handle_integrity(exc, f"product id={product_id}")
        return row

    def delete(self, product_id: int) -> None:
        """Delete a product; fails if price_logs still reference it."""
        row = self._session.get(Product, product_id)
        if row is None:
            raise NotFoundError(f"Product id={product_id} not found.")
        try:
            self._session.delete(row)
            self._session.flush()
        except IntegrityError as exc:
            _handle_integrity(
                exc,
                f"cannot delete product id={product_id} (price logs exist)",
            )


class PriceLogRepository:
    """CRUD for the price_logs fact table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        product_id: int,
        store_id: int,
        price_total: float,
        quantity: float,
        unit_type: str,
        date_recorded: str | date,
        notes: str | None = None,
    ) -> PriceLog:
        """Insert one price observation after validation."""
        price = validate_positive_number(price_total, "price_total")
        qty = validate_positive_number(quantity, "quantity")
        unit = validate_unit_type(unit_type)
        recorded = validate_date_recorded(date_recorded)
        note_text = validate_notes(notes)

        ProductRepository(self._session).get_by_id(product_id)
        StoreRepository(self._session).get_by_id(store_id)

        row = PriceLog(
            product_id=product_id,
            store_id=store_id,
            price_total=price,
            quantity=qty,
            unit_type=unit,
            date_recorded=recorded,
            notes=note_text,
        )
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            _handle_integrity(exc, "price log")
        return row

    def get_by_id(self, log_id: int) -> PriceLog:
        """Fetch one log with product and store relationships loaded."""
        row = self._session.scalar(
            select(PriceLog)
            .options(joinedload(PriceLog.product), joinedload(PriceLog.store))
            .where(PriceLog.log_id == log_id)
        )
        if row is None:
            raise NotFoundError(f"Price log id={log_id} not found.")
        return row

    def list_all(
        self,
        *,
        product_id: int | None = None,
        store_id: int | None = None,
        category_id: int | None = None,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
    ) -> list[PriceLog]:
        """
        List price logs with optional filters.

        Date filters use inclusive bounds (YYYY-MM-DD). Joins products when filtering by category.
        """
        stmt = (
            select(PriceLog)
            .options(joinedload(PriceLog.product), joinedload(PriceLog.store))
            .join(Product)
        )
        if product_id is not None:
            stmt = stmt.where(PriceLog.product_id == product_id)
        if store_id is not None:
            stmt = stmt.where(PriceLog.store_id == store_id)
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if start_date is not None:
            start = validate_date_recorded(start_date)
            stmt = stmt.where(PriceLog.date_recorded >= start)
        if end_date is not None:
            end = validate_date_recorded(end_date)
            stmt = stmt.where(PriceLog.date_recorded <= end)

        stmt = stmt.order_by(PriceLog.date_recorded.desc(), PriceLog.log_id.desc())
        return list(self._session.scalars(stmt).unique())

    def update(
        self,
        log_id: int,
        *,
        product_id: int | None = None,
        store_id: int | None = None,
        price_total: float | None = None,
        quantity: float | None = None,
        unit_type: str | None = None,
        date_recorded: str | date | None = None,
        notes: str | None = None,
    ) -> PriceLog:
        """Update any subset of fields on an existing log."""
        row = self.get_by_id(log_id)
        if product_id is not None:
            ProductRepository(self._session).get_by_id(product_id)
            row.product_id = product_id
        if store_id is not None:
            StoreRepository(self._session).get_by_id(store_id)
            row.store_id = store_id
        if price_total is not None:
            row.price_total = validate_positive_number(price_total, "price_total")
        if quantity is not None:
            row.quantity = validate_positive_number(quantity, "quantity")
        if unit_type is not None:
            row.unit_type = validate_unit_type(unit_type)
        if date_recorded is not None:
            row.date_recorded = validate_date_recorded(date_recorded)
        if notes is not None:
            row.notes = validate_notes(notes)
        try:
            self._session.flush()
        except IntegrityError as exc:
            _handle_integrity(exc, f"price log id={log_id}")
        return row

    def delete(self, log_id: int) -> None:
        """Remove a single price log row."""
        row = self.get_by_id(log_id)
        self._session.delete(row)
        self._session.flush()

    def insert_price_record(
        self,
        product_name: str,
        category_name: str,
        store_name: str,
        price_total: float,
        quantity: float,
        unit_type: str,
        date_recorded: str | date,
        notes: str | None = None,
    ) -> PriceLog:
        """
        High-level insert: resolve or create category, product, and store by name, then log price.

        Returns the new PriceLog. Suitable for UI form submission.
        """
        categories = CategoryRepository(self._session)
        products = ProductRepository(self._session)
        stores = StoreRepository(self._session)

        category = categories.get_or_create(category_name)
        store = stores.get_or_create(store_name)

        product = products.get_by_name(product_name)
        if product is None:
            product = products.create(product_name, category.category_id)
        elif product.category_id != category.category_id:
            raise ValidationError(
                f"Product '{product.product_name}' already exists under a different category.",
                field="category_name",
            )

        return self.create(
            product_id=product.product_id,
            store_id=store.store_id,
            price_total=price_total,
            quantity=quantity,
            unit_type=unit_type,
            date_recorded=date_recorded,
            notes=notes,
        )
