from enum import Enum


class WebhookEventType(str, Enum):
    FAX_CANCELLED = "fax.cancelled"
    FAX_CONVERTING = "fax.converting"
    FAX_DELIVERED = "fax.delivered"
    FAX_FAILED = "fax.failed"
    FAX_PARTIAL = "fax.partial"
    FAX_QUEUED = "fax.queued"
    FAX_RECEIVED = "fax.received"
    FAX_SENDING = "fax.sending"

    def __str__(self) -> str:
        return str(self.value)
