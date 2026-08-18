from enum import Enum


class ListFaxesInclude(str, Enum):
    ATTEMPTS = "attempts"

    def __str__(self) -> str:
        return str(self.value)
