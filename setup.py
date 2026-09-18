from __future__ import annotations

from config import get_settings
from bitrix import BitrixClient


STAGES = [
    ("NEW_CANDIDATE", "Новый кандидат", 10, "process"),
    ("NEEDS_CONTACT", "Требует связи", 20, "process"),
    ("CONTACTED", "Связались", 30, "process"),
    ("QUALIFICATION", "Квалификация", 40, "process"),
    ("INTERVIEW", "Интервью", 50, "process"),
    ("WAITING_DECISION", "Ожидаем решение", 60, "process"),
    ("SENT_TO_CLIENT", "Передан заказчику", 70, "process"),
    ("STARTED", "Выход на работу", 80, "success"),
    ("REJECTED", "Отказ", 90, "failure"),
]


def find_category(client: BitrixClient, name: str) -> dict | None:
    for category in client.list_categories():
        if category.get("name") == name:
            return category
    return None


def ensure_pipeline(client: BitrixClient, name: str) -> int:
    existing = find_category(client, name)
    if existing:
        return int(existing["id"])

    return client.add_category(name)


def ensure_stages(client: BitrixClient, category_id: int) -> None:
    existing_ids = {stage.get("STATUS_ID") for stage in client.list_stages(category_id)}

    for status_id, name, sort, semantics in STAGES:
        if status_id in existing_ids:
            continue
        client.add_stage(category_id, name, status_id, sort, semantics)


def setup() -> int:
    settings = get_settings()
    client = BitrixClient(settings.webhook)

    me = client.get_current_user()
    print(f"Connected as: {me.get('NAME', '')} {me.get('LAST_NAME', '')} (ID {me.get('ID')})")

    pipeline_id = ensure_pipeline(client, "Подбор персонала")
    print(f"Pipeline: Подбор персонала (ID {pipeline_id})")

    ensure_stages(client, pipeline_id)
    print(f"Stages configured: {len(STAGES)}")

    return pipeline_id
