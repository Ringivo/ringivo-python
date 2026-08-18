from enum import Enum


class FaxResolution(str, Enum):
    FINE = "fine"
    STANDARD = "standard"

    def __str__(self) -> str:
        return str(self.value)
