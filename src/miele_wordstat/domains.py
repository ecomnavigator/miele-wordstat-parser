from __future__ import annotations

from urllib.parse import urlparse


MARKETPLACE_HINTS = (
    "market.yandex",
    "ozon.",
    "wildberries.",
    "avito.",
    "megamarket.",
    "sbermegamarket.",
)

RETAILER_HINTS = (
    "mvideo.",
    "eldorado.",
    "dns-shop.",
    "citilink.",
    "holodilnik.",
    "hausdorf.",
    "technopark.",
    "vseinstrumenti.",
    "miele-store.",
    "bt-technika.",
)

SERVICE_HINTS = (
    "remont",
    "repair",
    "service",
    "servis",
    "master",
    "tehnik",
    "servicecenter",
)

CONTENT_HINTS = (
    "irecommend.",
    "otzovik.",
    "forum",
    "review",
    "reviews",
    "youtube.",
    "dzen.",
    "vc.",
)

OFFICIAL_DOMAINS = {
    "miele.ru",
    "miele.com",
}


def normalize_domain(value: object) -> str:
    raw = str(value or "").strip().casefold()
    if not raw:
        return "unknown"

    parsed = urlparse(raw if "://" in raw else f"//{raw}")
    host = parsed.hostname or raw.split("/")[0]
    host = host.strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host or "unknown"


def classify_competitor(domain: object) -> str:
    normalized = normalize_domain(domain)
    if normalized in OFFICIAL_DOMAINS or normalized.endswith(".miele.ru"):
        return "official"
    if any(hint in normalized for hint in MARKETPLACE_HINTS):
        return "marketplace"
    if any(hint in normalized for hint in SERVICE_HINTS):
        return "service_repair"
    if any(hint in normalized for hint in CONTENT_HINTS):
        return "content_review"
    if any(hint in normalized for hint in RETAILER_HINTS):
        return "retailer"
    return "unknown"
