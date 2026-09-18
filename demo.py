from __future__ import annotations

import random

from bitrix import BitrixClient
from schema import DEAL_FIELD_CODES


DEMO_COMMENT = "Синтетические демо-данные для тестовой презентации."

FIRST_NAMES = [
    "Василий", "Пётр", "Анна", "Сергей", "Ольга", "Дмитрий",
    "Екатерина", "Наталья", "Андрей", "Марина", "Александр", "Ирина",
    "Максим", "Елена", "Артём", "Виктория", "Роман", "Юлия",
]

LAST_NAMES = [
    "Петров", "Соколова", "Кузнецов", "Морозова", "Волков", "Лебедева",
    "Орлов", "Фёдорова", "Васильев", "Смирнова", "Иванов", "Попова",
]

VACANCIES = [
    "Водитель", "Курьер", "Оператор", "Менеджер по продажам",
    "Кладовщик", "Комплектовщик", "Администратор", "Водитель-экспедитор",
]

DIRECTIONS = {
    "Водитель": "Логистика",
    "Курьер": "Логистика",
    "Водитель-экспедитор": "Логистика",
    "Кладовщик": "Логистика",
    "Комплектовщик": "Производство",
    "Оператор": "Административный персонал",
    "Администратор": "Административный персонал",
    "Менеджер по продажам": "Продажи",
}

SOURCES = ["HH.ru", "Telegram", "Сайт", "Рекомендация"]
STAGES = [
    "Новый кандидат",
    "Требует связи",
    "Связались",
    "Квалификация",
    "Интервью",
    "Ожидаем решение",
    "Передан заказчику",
    "Выход на работу",
    "Отказ",
]


def stage_by_name(client: BitrixClient, category_id: int) -> dict[str, str]:
    return {item["NAME"]: item["STATUS_ID"] for item in client.list_stages(category_id)}


def reset_demo(client: BitrixClient, category_id: int) -> int:
    deals = client.list_deals(category_id)
    removed = 0

    for deal in deals:
        if deal.get("comments") == DEMO_COMMENT:
            client.delete_deal(int(deal["id"]))
            removed += 1

    print(f"Removed demo deals: {removed}")
    return removed


def random_candidate(index: int) -> tuple[str, str, str]:
    first = random.choice(FIRST_NAMES)

    # Roughly 60% of candidates have a surname already known.
    if random.random() < 0.6:
        surname = random.choice(LAST_NAMES)
        person = f"{first} {surname}"
    else:
        person = first

    vacancy = random.choice(VACANCIES)
    stage = random.choice(STAGES)
    return person, vacancy, stage


def seed_demo(
    client: BitrixClient,
    category_id: int,
    user_id: int,
    count: int = 30,
) -> None:
    stages = stage_by_name(client, category_id)

    for index in range(count):
        person, vacancy, stage_name = random_candidate(index)
        stage_id = stages.get(stage_name)

        if not stage_id:
            raise RuntimeError(f"Stage not found: {stage_name}")

        fields = {
            DEAL_FIELD_CODES["DESIRED_POSITION"]: vacancy,
            DEAL_FIELD_CODES["DIRECTION"]: DIRECTIONS[vacancy],
            DEAL_FIELD_CODES["VACANCY"]: vacancy,
            DEAL_FIELD_CODES["CLIENT_COMPANY"]: random.choice(
                ["ООО «Стандарт»", "ООО «Вектор»", "ООО «Логистик Плюс»"]
            ),
            DEAL_FIELD_CODES["CANDIDATE_SOURCE"]: random.choice(SOURCES),
            DEAL_FIELD_CODES["PRIORITY"]: random.choice(
                ["Высокий", "Средний", "Низкий"]
            ),
            DEAL_FIELD_CODES["BLOCKER"]: random.choice(
                [
                    "Нужно ответить",
                    "Не хватает информации",
                    "Ждём кандидата",
                    "Ждём заказчика",
                    "Назначить интервью",
                ]
            ),
            DEAL_FIELD_CODES["NEXT_STEP"]: random.choice(
                [
                    "Ответить кандидату",
                    "Позвонить кандидату",
                    "Уточнить опыт",
                    "Назначить интервью",
                    "Запросить документы",
                    "Уточнить решение",
                ]
            ),
        }

        client.add_deal(
            title=person,
            category_id=category_id,
            stage_id=stage_id,
            assigned_by_id=user_id,
            comments=DEMO_COMMENT,
            fields=fields,
        )

        print(f"Created: {person} — {vacancy} — {stage_name}")


def run(
    client: BitrixClient,
    category_id: int,
    user_id: int,
    count: int = 30,
) -> None:
    reset_demo(client, category_id)
    seed_demo(client, category_id, user_id, count=count)


def clear(client: BitrixClient, category_id: int) -> None:
    reset_demo(client, category_id)
