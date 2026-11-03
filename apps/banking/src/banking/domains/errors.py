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
