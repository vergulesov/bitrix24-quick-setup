from __future__ import annotations

from bitrix import BitrixClient
from config import get_settings


PROCESS_STAGES = [
    ("NEW_CANDIDATE", "Новый кандидат"),
    ("NEEDS_CONTACT", "Требует связи"),
    ("CONTACTED", "Связались"),
    ("QUALIFICATION", "Квалификация"),
    ("INTERVIEW", "Интервью"),
    ("WAITING_DECISION", "Ожидаем решение"),
    ("SENT_TO_CLIENT", "Передан заказчику"),
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

    # New Bitrix deal pipelines already contain final Success/Failure stages.
    # Reuse those system stages instead of creating additional final stages.
    success = next(
        (
            stage
            for stage in existing
            if stage.get("SEMANTICS") == "S"
            or stage.get("EXTRA", {}).get("SEMANTICS") == "success"
        ),
        None,
    )
    failure = next(
        (
            stage
            for stage in existing
            if stage.get("SEMANTICS") == "F"
            or stage.get("EXTRA", {}).get("SEMANTICS") in ("failure", "apology")
        ),
        None,
    )

    if not success or not failure:
        raise RuntimeError(
            "Bitrix final Success/Failure stages were not found in the pipeline."
        )

    existing_codes = {
        str(stage.get("STATUS_ID", "")).split(":", 1)[-1]
        for stage in existing
    }

    first_final_sort = min(
        int(success.get("SORT", 0) or 0),
        int(failure.get("SORT", 0) or 0),
    )

    missing = [
        item for item in PROCESS_STAGES
        if item[0] not in existing_codes
    ]

    if missing:
        step = max(1, first_final_sort // (len(missing) + 1))
        sort = step

        for status_id, name in missing:
            client.add_stage(
                category_id=category_id,
                name=name,
                status_id=status_id,
                sort=sort,
                semantics="",
            )
            sort += step

    # Rename the existing final stages to the business names we need.
    client.update_status(int(success["ID"]), {"NAME": "Выход на работу"})
    client.update_status(int(failure["ID"]), {"NAME": "Отказ"})


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
    print("Stages configured: 9")

    return pipeline_id
