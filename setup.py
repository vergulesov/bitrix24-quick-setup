from __future__ import annotations

from bitrix import BitrixClient
from config import get_settings


# Bitrix uses an empty semantics value for in-progress stages,
# "S" for success and "F" for failure.
STAGES = [
    ("NEW_CANDIDATE", "Новый кандидат", 10, ""),
    ("NEEDS_CONTACT", "Требует связи", 20, ""),
    ("CONTACTED", "Связались", 30, ""),
    ("QUALIFICATION", "Квалификация", 40, ""),
    ("INTERVIEW", "Интервью", 50, ""),
    ("WAITING_DECISION", "Ожидаем решение", 60, ""),
    ("SENT_TO_CLIENT", "Передан заказчику", 70, ""),
    ("STARTED", "Выход на работу", 80, "S"),
    ("REJECTED", "Отказ", 90, "F"),
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
    existing = client.list_stages(category_id)

    # For custom deal pipelines Bitrix may return codes such as C1:NEW_CANDIDATE.
    existing_codes = {
        str(stage.get("STATUS_ID", "")).split(":", 1)[-1]
        for stage in existing
    }

    for status_id, name, sort, semantics in STAGES:
        if status_id in existing_codes:
            continue

        client.add_stage(
            category_id=category_id,
            name=name,
            status_id=status_id,
            sort=sort,
            semantics=semantics,
        )


def setup() -> int:
    settings = get_settings()
    client = BitrixClient(settings.webhook)

    me = client.get_current_user()
    print(
        f"Connected as: {me.get('NAME', '')} "
        f"{me.get('LAST_NAME', '')} (ID {me.get('ID')})"
    )

    pipeline_id = ensure_pipeline(client, "Подбор персонала")
    print(f"Pipeline: Подбор персонала (ID {pipeline_id})")

    ensure_stages(client, pipeline_id)
    print(f"Stages configured: {len(STAGES)}")

    return pipeline_id
