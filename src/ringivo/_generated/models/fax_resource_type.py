from enum import Enum


class FaxResourceType(str, Enum):
    FAXES = "faxes"

    def __str__(self) -> str:
        return str(self.value)
