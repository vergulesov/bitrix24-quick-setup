from __future__ import annotations

from bitrix import BitrixClient


DEMO_CANDIDATES = [
    ("Василий", "Водитель", "Новый кандидат"),
    ("Пётр", "Курьер", "Требует связи"),
    ("Анна", "Оператор", "Связались"),
    ("Сергей", "Менеджер по продажам", "Квалификация"),
    ("Ольга", "Оператор", "Интервью"),
    ("Дмитрий", "Водитель", "Ожидаем решение"),
    ("Екатерина", "Менеджер по продажам", "Передан заказчику"),
    ("Наталья", "Оператор", "Выход на работу"),
    ("Андрей", "Курьер", "Отказ"),
    ("Марина", "Водитель", "Требует связи"),
    ("Александр", "Кладовщик", "Новый кандидат"),
    ("Новый кандидат", "Водитель", "Новый кандидат"),
]

DEMO_COMMENT = "Синтетические демо-данные для тестовой презентации."


def stage_by_name(client: BitrixClient, category_id: int) -> dict[str, str]:
    return {item["NAME"]: item["STATUS_ID"] for item in client.list_stages(category_id)}


def reset_demo(client: BitrixClient, category_id: int) -> None:
    for deal in client.list_deals(category_id):
        if deal.get("comments") == DEMO_COMMENT:
            client.delete_deal(int(deal["id"]))
            print(f"Removed demo: {deal.get('title', deal['id'])}")


def seed_demo(client: BitrixClient, category_id: int, user_id: int) -> None:
    stages = stage_by_name(client, category_id)

    for person, vacancy, stage_name in DEMO_CANDIDATES:
        stage_id = stages.get(stage_name)
        if not stage_id:
            raise RuntimeError(f"Stage not found: {stage_name}")

        client.add_deal(
            title=person,
            category_id=category_id,
            stage_id=stage_id,
            assigned_by_id=user_id,
            comments=DEMO_COMMENT,
        )
        print(f"Created: {person} — {vacancy}")


def run(client: BitrixClient, category_id: int, user_id: int) -> None:
    reset_demo(client, category_id)
    seed_demo(client, category_id, user_id)
