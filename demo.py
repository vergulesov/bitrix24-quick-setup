from __future__ import annotations

from bitrix import BitrixClient


DEMO_CANDIDATES = [
    ("Алексей Петров", "Менеджер по продажам", "Новый кандидат"),
    ("Мария Соколова", "Менеджер по продажам", "Требует связи"),
    ("Иван Кузнецов", "Менеджер по продажам", "Связались"),
    ("Ольга Морозова", "Оператор", "Квалификация"),
    ("Дмитрий Волков", "Оператор", "Интервью"),
    ("Екатерина Лебедева", "Менеджер по продажам", "Ожидаем решение"),
    ("Сергей Орлов", "Менеджер по продажам", "Передан заказчику"),
    ("Наталья Фёдорова", "Оператор", "Выход на работу"),
    ("Андрей Васильев", "Менеджер по продажам", "Отказ"),
]


def stage_by_name(client: BitrixClient, category_id: int) -> dict[str, str]:
    return {item["NAME"]: item["STATUS_ID"] for item in client.list_stages(category_id)}


def seed_demo(client: BitrixClient, category_id: int, user_id: int) -> None:
    stages = stage_by_name(client, category_id)

    for person, vacancy, stage_name in DEMO_CANDIDATES:
        stage_id = stages.get(stage_name)
        if not stage_id:
            raise RuntimeError(f"Stage not found: {stage_name}")

        client.add_deal(
            title=f"{person} — {vacancy}",
            category_id=category_id,
            stage_id=stage_id,
            assigned_by_id=user_id,
            comments="Синтетические демо-данные для тестовой презентации.",
        )
        print(f"Created: {person}")


def run(client: BitrixClient, category_id: int, user_id: int) -> None:
    seed_demo(client, category_id, user_id)
