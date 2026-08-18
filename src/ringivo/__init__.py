"""Ringivo API client. Pre-release: the full client arrives in 0.1.0."""


class Ringivo:
    def __init__(self, base_url: str, client_id: str, client_secret: str) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        self.base_url = base_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret


__all__ = ["Ringivo"]
