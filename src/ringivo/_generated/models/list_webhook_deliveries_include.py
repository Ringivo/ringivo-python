from enum import Enum


class ListWebhookDeliveriesInclude(str, Enum):
    ENDPOINT = "endpoint"

    def __str__(self) -> str:
        return str(self.value)
