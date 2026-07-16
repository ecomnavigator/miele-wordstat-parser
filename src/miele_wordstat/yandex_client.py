from __future__ import annotations

from typing import Any

import requests


class YandexSearchApiError(RuntimeError):
    pass


class YandexWordstatClient:
    """Thin client for Yandex Search API methods."""

    WEB_SEARCH_URL = "https://searchapi.api.cloud.yandex.net/v2/web/search"

    def __init__(self, api_key: str, folder_id: str | None = None) -> None:
        self.api_key = api_key
        self.folder_id = folder_id

    def web_search(
        self,
        query: str,
        region: int,
        *,
        page: int = 0,
        groups_on_page: int = 1,
        docs_in_group: int = 1,
        timeout: int = 30,
    ) -> dict[str, Any]:
        if not self.folder_id:
            raise YandexSearchApiError("YANDEX_FOLDER_ID is required")

        payload = {
            "query": {
                "searchType": "SEARCH_TYPE_RU",
                "queryText": query,
                "familyMode": "FAMILY_MODE_MODERATE",
                "page": str(page),
                "fixTypoMode": "FIX_TYPO_MODE_ON",
            },
            "groupSpec": {
                "groupMode": "GROUP_MODE_FLAT",
                "groupsOnPage": str(groups_on_page),
                "docsInGroup": str(docs_in_group),
            },
            "region": str(region),
            "l10n": "LOCALIZATION_RU",
            "folderId": self.folder_id,
            "responseFormat": "FORMAT_XML",
            "userAgent": "miele-wordstat-parser/0.1",
        }
        response = requests.post(
            self.WEB_SEARCH_URL,
            headers={"Authorization": f"Api-Key {self.api_key}"},
            json=payload,
            timeout=timeout,
        )
        if response.status_code >= 400:
            body = response.text[:500].replace("\n", " ")
            raise YandexSearchApiError(
                f"Yandex Search API returned HTTP {response.status_code}: {body}"
            )
        return response.json()

    def get_dynamics(self, query: str, region: int) -> dict:
        raise NotImplementedError
