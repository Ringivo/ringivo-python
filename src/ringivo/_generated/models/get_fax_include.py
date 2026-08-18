from enum import Enum


class GetFaxInclude(str, Enum):
    ATTEMPTS = "attempts"

    def __str__(self) -> str:
        return str(self.value)
