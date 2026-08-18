from enum import Enum


class FaxUpdateRequestDataType(str, Enum):
    FAXES = "faxes"

    def __str__(self) -> str:
        return str(self.value)
