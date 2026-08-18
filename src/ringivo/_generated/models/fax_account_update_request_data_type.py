from enum import Enum


class FaxAccountUpdateRequestDataType(str, Enum):
    FAX_ACCOUNTS = "fax-accounts"

    def __str__(self) -> str:
        return str(self.value)
