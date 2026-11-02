"""The "same as last time" rule: which past label to suggest for an operation."""

from collections.abc import Iterable

from banking.domains.label import LabelFields, LabelSource, PastLabel, Suggestion


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


def suggest(history: Iterable[PastLabel], description: str) -> Suggestion | None:
    """The category of the latest labelled operation with the same key.

    None without a match, or when nothing is left of the description to match on:
    never a guess.
    """
    if not (key := match_key(description)):
        return None
    matches = [past for past in history if match_key(past.description) == key]
    if not matches:
        return None
    latest = max(matches, key=lambda past: (past.operation_date, past.operation_id))
    return Suggestion(latest.category_id, latest.operation_date)


def source_of(fields: LabelFields, suggestion: Suggestion | None) -> LabelSource:
    """`suggestion` if the label is the one suggested, else `manual`."""
    if suggestion is not None and fields.category_id == suggestion.category_id:
        return LabelSource.SUGGESTION
    return LabelSource.MANUAL
