from enum import Enum


class FaxAccountStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"

    def __str__(self) -> str:
        return str(self.value)
