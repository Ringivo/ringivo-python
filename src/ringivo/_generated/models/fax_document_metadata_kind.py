from enum import Enum


class FaxDocumentMetadataKind(str, Enum):
    PDF = "pdf"
    SOURCE = "source"
    THUMB = "thumb"
    TIFF = "tiff"

    def __str__(self) -> str:
        return str(self.value)
