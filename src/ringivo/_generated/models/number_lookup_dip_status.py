from enum import Enum


class NumberLookupDipStatus(str, Enum):
    ANSWERED = "answered"
    FAILED = "failed"
    NO_DATA = "no_data"

    def __str__(self) -> str:
        return str(self.value)
