from enum import Enum


class FaxAttemptResourceType(str, Enum):
    FAX_ATTEMPTS = "fax-attempts"

    def __str__(self) -> str:
        return str(self.value)
