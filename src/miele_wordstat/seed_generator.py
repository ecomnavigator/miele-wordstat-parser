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
]


def generate_probe_seed_file(path: Path, limit: int, region: int) -> int:
    rows: list[tuple[str, str, int]] = []
    for product, category in PRODUCTS:
        for modifier in MODIFIERS:
            if modifier:
                query = f"{modifier} {product} miele"
            else:
                query = f"{product} miele"
            rows.append((query, category, region))
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
