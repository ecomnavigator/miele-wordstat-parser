from __future__ import annotations


class YandexWordstatClient:
    """Thin client for Yandex Wordstat Search API methods."""

    def __init__(self, api_key: str, folder_id: str | None = None) -> None:
        self.api_key = api_key
        self.folder_id = folder_id

    def get_top(self, query: str, region: int) -> dict:
        raise NotImplementedError

    def get_dynamics(self, query: str, region: int) -> dict:
        raise NotImplementedError
