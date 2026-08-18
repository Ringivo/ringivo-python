from enum import Enum


class FaxAccountUserResourceType(str, Enum):
    FAX_ACCOUNT_USERS = "fax-account-users"

    def __str__(self) -> str:
        return str(self.value)
