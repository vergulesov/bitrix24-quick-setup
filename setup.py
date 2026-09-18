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

    # Bitrix requires: In Progress -> Success -> Failure.
    # Put our process stages before the first final stage.
    final_sorts = [
        int(stage.get("SORT", 0) or 0)
        for stage in existing
        if stage.get("SEMANTICS") in ("S", "F")
    ]
    first_final_sort = min(final_sorts, default=1000)

    # Reserve enough room below the first final stage.
    missing_process = [
        item for item in STAGES
        if item[0] not in existing_codes and item[3] == ""
    ]
    process_step = max(1, first_final_sort // (len(missing_process) + 1))

    sort = process_step
    for status_id, name, _configured_sort, semantics in STAGES:
        if status_id in existing_codes:
            continue

        if semantics == "":
            stage_sort = sort
            sort += process_step
            if stage_sort >= first_final_sort:
                raise RuntimeError(
                    "Not enough SORT space before Bitrix final stages"
                )
        elif semantics == "S":
            # Keep success before failure.
            stage_sort = first_final_sort
        else:
            stage_sort = max(
                [int(stage.get("SORT", 0) or 0) for stage in existing]
                + [first_final_sort]
            ) + 10

        client.add_stage(
            category_id=category_id,
            name=name,
            status_id=status_id,
            sort=stage_sort,
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
