"""Package-specific exceptions."""


class AuthUnavailableError(RuntimeError):
    """Authenticated operation cannot be initialized safely."""


class StorageError(RuntimeError):
    """SQLite operation failed."""
