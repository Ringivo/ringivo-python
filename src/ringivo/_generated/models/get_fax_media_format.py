from enum import Enum


class GetFaxMediaFormat(str, Enum):
    PDF = "pdf"
    TIFF = "tiff"

    def __str__(self) -> str:
        return str(self.value)
