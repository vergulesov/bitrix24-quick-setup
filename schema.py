from __future__ import annotations

from typing import Any


DEAL_FIELD_SPECS: list[dict[str, Any]] = [
    {
        "field_name": "CANDIDATE_PHONE",
        "label": "Телефон",
        "type": "string",
        "sort": 100,
    },
    {
        "field_name": "DESIRED_POSITION",
        "label": "Желаемая должность",
        "type": "string",
        "sort": 110,
    },
    {
        "field_name": "DIRECTION",
        "label": "Направление",
        "type": "enumeration",
        "sort": 120,
        "values": [
            "IT",
            "Продажи",
            "Производство",
            "Строительство",
            "Логистика",
            "Административный персонал",
            "Другое",
        ],
    },
    {
        "field_name": "VACANCY",
        "label": "Вакансия",
        "type": "string",
        "sort": 130,
    },
    {
        "field_name": "CLIENT_COMPANY",
        "label": "Заказчик",
        "type": "string",
        "sort": 140,
    },
    {
        "field_name": "CANDIDATE_SOURCE",
        "label": "Источник",
        "type": "enumeration",
        "sort": 150,
        "values": [
            "HH.ru",
            "Telegram",
            "Сайт",
            "Рекомендация",
            "Другое",
        ],
    },
    {
        "field_name": "LAST_INBOUND_AT",
        "label": "Последний входящий",
        "type": "datetime",
        "sort": 200,
    },
    {
        "field_name": "LAST_RESPONSE_AT",
        "label": "Последний ответ",
        "type": "datetime",
        "sort": 210,
    },
    {
        "field_name": "RESPONSE_DEADLINE",
        "label": "Срок реакции",
        "type": "datetime",
        "sort": 220,
    },
    {
        "field_name": "PRIORITY",
        "label": "Приоритет",
        "type": "enumeration",
        "sort": 230,
        "values": [
            "Высокий",
            "Средний",
            "Низкий",
        ],
    },
    {
        "field_name": "BLOCKER",
        "label": "Блокер",
        "type": "enumeration",
        "sort": 240,
        "values": [
            "Нужно ответить",
            "Не хватает информации",
            "Ждём кандидата",
            "Ждём заказчика",
            "Назначить интервью",
            "Другое",
        ],
    },
    {
        "field_name": "NEXT_STEP",
        "label": "Следующий шаг",
        "type": "string",
        "sort": 250,
    },
    {
        "field_name": "NEXT_ACTION_AT",
        "label": "Дата следующего действия",
        "type": "datetime",
        "sort": 260,
    },
]


DEAL_FIELD_CODES = {
    item["field_name"]: f"UF_CRM_{item['field_name']}"
    for item in DEAL_FIELD_SPECS
}
