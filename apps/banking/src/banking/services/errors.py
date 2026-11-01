"""Domain errors raised by services; the API layer turns them into responses."""


class NotFoundError(Exception):
    """The requested item doesn't exist."""


class InvalidError(Exception):
    """The input breaks a business rule; `field` is the input at fault."""

    def __init__(self, field: str, message: str) -> None:
        """Name the field at fault and say why."""
        super().__init__(message)
        self.field = field
        self.message = message


class ConflictError(Exception):
    """The request conflicts with the item's current state."""

    def __init__(self, message: str) -> None:
        """Say what the conflict is."""
        super().__init__(message)
        self.message = message
