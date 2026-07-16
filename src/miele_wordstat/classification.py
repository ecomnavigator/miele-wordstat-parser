from __future__ import annotations


INTENT_KEYWORDS = {
    "buy": [
        "купить",
        "цена",
        "магазин",
        "акция",
        "скидка",
        "распродажа",
        "доставка",
    ],
    "service": [
        "ремонт",
        "сервис",
        "сервисный",
        "неисправность",
        "не работает",
        "не включается",
        "ошибка",
        "замена",
    ],
    "parts": ["запчасти", "фильтр", "мешки", "средство", "расходники", "оригинал"],
    "research": [
        "отзывы",
        "обзор",
        "характеристики",
        "размеры",
        "сравнение",
        "лучший",
        "форум",
    ],
    "manual": ["инструкция", "подключение", "установка", "гарантия"],
    "brand": ["официальный сайт"],
}

SUPER_INTENT_BY_INTENT = {
    "buy": "commercial",
    "service": "commercial",
    "parts": "commercial",
    "brand": "commercial",
    "research": "informational",
    "manual": "informational",
    "generic": "informational",
}


def infer_intent(query: str, stored_intent: object = None) -> str:
    if isinstance(stored_intent, str) and stored_intent.strip():
        return stored_intent
    normalized = query.casefold()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return intent
    return "generic"


def infer_super_intent(intent: str) -> str:
    return SUPER_INTENT_BY_INTENT.get(intent, "informational")


def resolve_super_intent(intent: str, stored_super_intent: object = None) -> str:
    if isinstance(stored_super_intent, str) and stored_super_intent.strip():
        return stored_super_intent
    return infer_super_intent(intent)
