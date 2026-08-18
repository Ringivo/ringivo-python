from enum import Enum


class WebhookEndpointResourceType(str, Enum):
    WEBHOOK_ENDPOINTS = "webhook-endpoints"

    def __str__(self) -> str:
        return str(self.value)
