from enum import Enum


class ErrorCode(str, Enum):
    CALLER_ID_NOT_PERMITTED = "caller_id_not_permitted"
    DOCUMENT_TOO_LARGE = "document_too_large"
    FAX_ACCOUNT_SUSPENDED = "fax_account_suspended"
    FORBIDDEN = "forbidden"
    INTERNAL_ERROR = "internal_error"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    TOO_MANY_PAGES = "too_many_pages"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    VALIDATION_FAILED = "validation_failed"

    def __str__(self) -> str:
        return str(self.value)
