from __future__ import annotations

import csv
from pathlib import Path


PRODUCTS = [
    ("стиральная машина", "washing_machine"),
    ("посудомоечная машина", "dishwasher"),
    ("сушильная машина", "dryer"),
    ("пылесос", "vacuum"),
    ("робот пылесос", "robot_vacuum"),
    ("духовой шкаф", "oven"),
    ("варочная панель", "hob"),
    ("кофемашина", "coffee_machine"),
    ("холодильник", "refrigerator"),
    ("морозильник", "freezer"),
    ("вытяжка", "hood"),
    ("пароварка", "steam_oven"),
    ("микроволновка", "microwave"),
    ("гладильная система", "ironing_system"),
]

MODIFIERS = [
    "",
    "купить",
    "цена",
    "официальный сайт",
    "интернет магазин",
    "отзывы",
    "ремонт",
    "сервисный центр",
    "запчасти",
    "инструкция",
    "ошибка",
    "фильтр",
    "мешки",
    "средство",
    "акция",
    "скидка",
    "распродажа",
    "доставка",
    "установка",
    "подключение",
    "гарантия",
    "неисправность",
    "не включается",
    "не работает",
    "замена",
    "оригинал",
    "расходники",
    "сравнение",
    "лучший",
    "новый",
    "б у",
    "бу",
    "форум",
    "обзор",
    "характеристики",
    "размеры",
    "встраиваемый",
]


def generate_probe_seed_file(path: Path, limit: int, region: int) -> int:
    rows: list[tuple[str, str, int]] = []
    seen: set[str] = set()
    for product, category in PRODUCTS:
        for modifier in MODIFIERS:
            candidates = [
                f"{product} miele",
                f"{product} миле",
                f"miele {product}",
            ]
            if modifier:
                candidates.extend(
                    [
                        f"{modifier} {product} miele",
                        f"{modifier} {product} миле",
                        f"{product} miele {modifier}",
                        f"{product} миле {modifier}",
                        f"miele {product} {modifier}",
                    ]
                )
            for query in candidates:
                normalized = " ".join(query.split()).casefold()
                if normalized in seen:
                    continue
                seen.add(normalized)
                rows.append((query, category, region))
                if len(rows) >= limit:
                    break
            if len(rows) >= limit:
                break
        if len(rows) >= limit:
            break

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["query", "category", "region"])
        writer.writerows(rows)
    return len(rows)
