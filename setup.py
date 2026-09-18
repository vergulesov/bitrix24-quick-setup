from __future__ import annotations

from bitrix import BitrixClient
from config import get_settings


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

    existing_codes = {
        str(stage.get("STATUS_ID", "")).split(":", 1)[-1]
        for stage in existing
    }

    # Bitrix requires process stages first, then success, then failure.
    # Start after existing stages to avoid colliding with system final stages.
    max_sort = max((int(stage.get("SORT", 0) or 0) for stage in existing), default=0)
    process_sort = max_sort + 10

    for status_id, name, _sort, semantics in STAGES:
        if status_id in existing_codes:
            continue

        if semantics == "":
            sort = process_sort
            process_sort += 10
        elif semantics == "S":
            sort = process_sort
            process_sort += 10
        else:
            sort = process_sort
            process_sort += 10

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
