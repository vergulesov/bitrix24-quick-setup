from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bitrix import BitrixClient
from schema import DEAL_FIELD_CODES

DEMO_COMMENT = "Синтетические SLA-демо-данные для тестовой презентации."

CASES = [
    ("Alexey Petrov", "Водитель", "Новый кандидат", "Высокий", "Не ответил кандидату", "Ответить кандидату", -95, False),
    ("Marina Sokolova", "Кладовщик", "New candidate", "High", "No response", "Reply to candidate", -35, False),
    ("Dmitry Volkov", "Курьер", "New candidate", "Средний", "No response", "Reply to candidate", 25, False),
    ("Olga Morozova", "Оператор", "New candidate", "High", "Не хватает информации", "Уточнить условия", 70, False),
    ("Sergey Orlov", "Комплектовщик", "New candidate", "Низкий", "No response", "Reply to candidate", 115, False),
    ("Irina Lebedeva", "Менеджер по продажам", "New candidate", "Medium", "Ответ получен", "Провести квалификацию", 180, True),
    ("Artem Vasiliev", "Driver", "Квалификация", "High", "Missing information", "Уточнить опыт", 45, True),
    ("Elena Fedorova", "Courier", "Qualification", "Medium", "Назначить интервью", "Согласовать время интервью", 120, True),
    ("Petr Kuznetsov", "Operator", "Qualification", "Low", "Missing information", "Запросить документы", 240, True),
    ("Anna Popova", "Warehouse", "Интервью", "High", "Interview to schedule", "Провести интервью", 30, True),
    ("Maxim Vlasov", "Driver", "Interview", "Medium", "Ждём кандидата", "Подтвердить интервью", 90, True),
    ("Yulia Smirnova", "Администратор", "Interview", "Low", "Waiting candidate", "Получить подтверждение", 210, True),
    ("Victor Ivanov", "Sales manager", "Ожидаем решение", "High", "Ждём заказчика", "Уточнить решение заказчика", 60, True),
    ("Roman Orlov", "Driver", "Waiting decision", "Medium", "Waiting candidate", "Get confirmation", 150, True),
    ("Natalia Volkova", "Warehouse", "Документы", "High", "Missing information", "Проверить документы", 75, True),
    ("Alexander Sidorov", "Picker", "Documents", "Medium", "Waiting candidate", "Получить комплект документов", 300, True),
    ("Ekaterina Petrova", "Operator", "Передан заказчику", "High", "Waiting client", "Получить обратную связь", 40, True),
    ("Andrey Morozov", "Courier", "Выход на работу", "Medium", "Другое", "Контроль выхода", 360, True),
]

def stage_map(client: BitrixClient, category_id: int) -> dict[str, str]:
    return {x["NAME"]: x["STATUS_ID"] for x in client.list_stages(category_id)}

def clear_sla_demo(client: BitrixClient, category_id: int) -> int:
    removed = 0
    while True:
        data = client.call("crm.item.list", {
            "entityTypeId": 2,
            "select": ["id", "comments"],
            "filter": {"categoryId": category_id},
        })
        items = data.get("items", [])
        if not items:
            break
        found = False
        for item in items:
            if item.get("comments") == DEMO_COMMENT:
                client.delete_deal(int(item["id"]))
                removed += 1
                found = True
        if not found:
            break
    return removed

def run(client: BitrixClient, category_id: int, user_id: int) -> None:
    stages = stage_map(client, category_id)
    now = datetime.now(timezone.utc)
    print("Creating deterministic SLA demo...")

    for person, vacancy, stage_name, priority, blocker, next_step, deadline_delta, responded in CASES:
        stage_id = stages.get(stage_name)
        if not stage_id:
            raise RuntimeError(f"Stage not found: {stage_name}")

        deadline = now + timedelta(minutes=deadline_delta)
        inbound = deadline - timedelta(hours=2)
        response = inbound + timedelta(minutes=35) if responded else None
        next_action = now + timedelta(minutes=max(10, deadline_delta))

        first, last = person.split(" ", 1)
        fields = {
            DEAL_FIELD_CODES["CANDIDATE_FIRST_NAME"]: first,
            DEAL_FIELD_CODES["CANDIDATE_LAST_NAME"]: last,
            DEAL_FIELD_CODES["CANDIDATE_PHONE"]: f"+7900{1000000 + len(person) * 137}",
            DEAL_FIELD_CODES["DESIRED_POSITION"]: vacancy,
            DEAL_FIELD_CODES["VACANCY"]: vacancy,
            DEAL_FIELD_CODES["CANDIDATE_SOURCE"]: "StaffFlow Demo",
            DEAL_FIELD_CODES["LAST_INBOUND_AT"]: inbound.isoformat(timespec="seconds"),
            DEAL_FIELD_CODES["LAST_RESPONSE_AT"]: response.isoformat(timespec="seconds") if response else "",
            DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
            DEAL_FIELD_CODES["PRIORITY"]: priority,
            DEAL_FIELD_CODES["BLOCKER"]: blocker,
            DEAL_FIELD_CODES["NEXT_STEP"]: next_step,
            DEAL_FIELD_CODES["NEXT_ACTION_AT"]: next_action.isoformat(timespec="seconds"),
        }

        deal_id = client.add_deal(
            title=f"{person} · {vacancy}",
            category_id=category_id,
            stage_id=stage_id,
            assigned_by_id=user_id,
            comments=DEMO_COMMENT,
            fields=fields,
        )
        client.add_timeline_comment(
            deal_id,
            f"[SLA DEMO] Incoming: candidate asks about vacancy {vacancy}.",
        )
        if responded:
            client.add_timeline_comment(deal_id, "[SLA DEMO] Recruiter replied.")

        print(f"{deal_id}: {person} | {stage_name} | {priority} | deadline {deadline.isoformat(timespec='minutes')}")
