"""The "same as last time" rule: which past label to suggest for an operation."""

from collections.abc import Iterable, Mapping, Sequence

from banking.domains.label import LabelFields, LabelSource, PastLabel, Suggestion
from banking.domains.operation import Operation


def match_key(description: str) -> str:
    """The description without its noise; operations with the same key are the same.

    Every word holding a digit is dropped (card date, card number, references), case
    and spacing are ignored.
    """
    return " ".join(
        word
        for word in description.upper().split()
        if not any(char.isdigit() for char in word)
    )


def latest_by_key(history: Iterable[PastLabel]) -> Mapping[str, Suggestion]:
    """The latest label's category for each key, in one pass over the history.

    An empty key (nothing left to match on) gets nothing: never a guess.
    """
    latest: dict[str, PastLabel] = {}
    for past in history:
        if not (key := match_key(past.description)):
            continue
        current = latest.get(key)
        if current is None or (past.operation_date, past.operation_id) > (
            current.operation_date,
            current.operation_id,
        ):
            latest[key] = past
    return {
        key: Suggestion(past.category_id, past.operation_date)
        for key, past in latest.items()
    }


def suggest(history: Iterable[PastLabel], description: str) -> Suggestion | None:
    """The category of the latest labelled operation with the same key, if any."""
    return latest_by_key(history).get(match_key(description))


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


def source_of(fields: LabelFields, suggestion: Suggestion | None) -> LabelSource:
    """`suggestion` if the label is the one suggested, else `manual`."""
    if suggestion is not None and fields.category_id == suggestion.category_id:
        return LabelSource.SUGGESTION
    return LabelSource.MANUAL
