"""
Data Access Layer (DAL) for SQLite via SQLAlchemy.

Responsibilities (future):
- Connection/session management for `data/tracker.db`
- CRUD on `stores`, `products`, and `price_logs`
- Parameterized queries only (no SQL string interpolation from user input)
- Transaction error handling with safe rollback

The UI must never construct raw SQL; all persistence goes through this module.
"""
