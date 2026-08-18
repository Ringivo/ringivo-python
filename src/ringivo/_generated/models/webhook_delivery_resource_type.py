from enum import Enum


class WebhookDeliveryResourceType(str, Enum):
    WEBHOOK_DELIVERIES = "webhook-deliveries"

    def __str__(self) -> str:
        return str(self.value)
