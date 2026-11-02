"""Similar operations: the same payee, whatever the card date or reference."""

from collections.abc import Iterable, Sequence

from banking.domains.operation import Operation


def match_key(description: str) -> str:
    """The description without its noise; operations with the same key are similar.

    Every word holding a digit is dropped (card date, card number, references), case
    and spacing are ignored.
    """
    return " ".join(
        word
        for word in description.upper().split()
        if not any(char.isdigit() for char in word)
    )


def similar_ids(operation: Operation, others: Iterable[Operation]) -> Sequence[int]:
    """The ids of the operations sharing the operation's key, itself included.

    Only the operation itself when its key is empty: nothing to match on.
    """
    key = match_key(operation.description)
    return [
        other.id
        for other in others
        if other.id == operation.id or (key and match_key(other.description) == key)
    ]
