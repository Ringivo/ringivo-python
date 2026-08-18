from enum import Enum


class WebhookDeliveryStatus(str, Enum):
    DEAD = "dead"
    DELIVERED = "delivered"
    PENDING = "pending"

    def __str__(self) -> str:
        return str(self.value)
