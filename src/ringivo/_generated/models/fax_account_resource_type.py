from enum import Enum


class FaxAccountResourceType(str, Enum):
    FAX_ACCOUNTS = "fax-accounts"

    def __str__(self) -> str:
        return str(self.value)
