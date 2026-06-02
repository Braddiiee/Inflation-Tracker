"""Database-layer exceptions used by repositories and connection management."""


class DatabaseError(Exception):
    """Base exception for persistence failures (connection, query, constraint)."""


class ValidationError(Exception):
    """Raised when input fails business rules before touching the database."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class NotFoundError(DatabaseError):
    """Raised when a requested row does not exist."""
