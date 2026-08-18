from enum import Enum


class PhoneNumberResourceType(str, Enum):
    PHONE_NUMBERS = "phone-numbers"

    def __str__(self) -> str:
        return str(self.value)
