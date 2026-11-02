"""Labels: what an operation was for."""

from enum import StrEnum


class LabelSource(StrEnum):
    """How a label was set; the share of suggestions accepted is a success metric."""

    SUGGESTION = "suggestion"
    MANUAL = "manual"
