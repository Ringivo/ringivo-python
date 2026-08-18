from enum import Enum


class FaxFailureCodeType3Type1(str, Enum):
    BUSY = "busy"
    CARRIER_REJECTED = "carrier_rejected"
    DOCUMENT_ERROR = "document_error"
    INCOMPATIBLE = "incompatible"
    INTERNAL_ERROR = "internal_error"
    INVALID_NUMBER = "invalid_number"
    LINE_DROPPED = "line_dropped"
    LINE_QUALITY = "line_quality"
    NEGOTIATION_FAILED = "negotiation_failed"
    NO_ANSWER = "no_answer"
    NO_FAX_TONE = "no_fax_tone"

    def __str__(self) -> str:
        return str(self.value)
