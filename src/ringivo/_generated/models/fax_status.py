from enum import Enum


class FaxStatus(str, Enum):
    CANCELLED = "cancelled"
    CONVERTING = "converting"
    DELIVERED = "delivered"
    FAILED = "failed"
    PARTIAL = "partial"
    QUEUED = "queued"
    RECEIVED = "received"
    SENDING = "sending"

    def __str__(self) -> str:
        return str(self.value)
