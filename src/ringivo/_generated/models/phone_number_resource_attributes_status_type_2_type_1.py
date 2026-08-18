from enum import Enum


class PhoneNumberResourceAttributesStatusType2Type1(str, Enum):
    ACTIVE = "active"
    FAILED = "failed"
    PENDING = "pending"
    RELEASING = "releasing"

    def __str__(self) -> str:
        return str(self.value)
