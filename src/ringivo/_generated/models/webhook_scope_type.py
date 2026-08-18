from enum import Enum


class WebhookScopeType(str, Enum):
    CUSTOMER = "customer"
    FAX_ACCOUNT = "fax_account"
    TENANT = "tenant"

    def __str__(self) -> str:
        return str(self.value)
