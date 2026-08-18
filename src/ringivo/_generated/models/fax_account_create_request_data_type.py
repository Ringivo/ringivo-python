from enum import Enum


class FaxAccountCreateRequestDataType(str, Enum):
    FAX_ACCOUNTS = "fax-accounts"

    def __str__(self) -> str:
        return str(self.value)
