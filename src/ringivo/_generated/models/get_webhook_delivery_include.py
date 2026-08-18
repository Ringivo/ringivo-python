from enum import Enum


class GetWebhookDeliveryInclude(str, Enum):
    ENDPOINT = "endpoint"

    def __str__(self) -> str:
        return str(self.value)
