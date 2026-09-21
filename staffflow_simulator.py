import os
import random
import threading
import time
import traceback
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

from schema import DEAL_FIELD_CODES

load_dotenv()

WEBHOOK = os.getenv("BITRIX_WEBHOOK_URL") or os.getenv("BITRIX_WEBHOOK")
if not WEBHOOK:
    raise SystemExit("Не найден BITRIX_WEBHOOK_URL / BITRIX_WEBHOOK в .env")

PIPELINE_NAME = "Подбор персонала"
DEMO_COMMENT = "SLA DEMO DATA"
CONNECTOR_URL = os.getenv("STAFFFLOW_CONNECTOR_URL", "https://195-19-195-13.sslip.io/bitrix/app")
CONNECTOR_TOKEN = os.getenv("STAFFFLOW_SEND_TOKEN", "")
CONNECTOR_ID = "staffflow_test"
OPEN_LINE_ID = 1
SLA_MINUTES = 120

WORKDAY_SCENARIO = [
    {"name":"Алексей","vacancy":"Водитель","priority":"Высокий","stage":"Новый кандидат","delta":-90,"answered":False,"next":"Ответить кандидату","blocker":"Нет ответа кандидату","comment":"Новый входящий. SLA уже просрочен."},
    {"name":"Марина","vacancy":"Кладовщик","priority":"Высокий","stage":"Новый кандидат","delta":-40,"answered":False,"next":"Ответить кандидату","blocker":"Нет ответа кандидату","comment":"Новый входящий. SLA уже просрочен."},
    {"name":"Дмитрий","vacancy":"Курьер","priority":"Высокий","stage":"Новый кандидат","delta":-15,"answered":False,"next":"Ответить кандидату","blocker":"Нет ответа кандидату","comment":"Новый входящий. SLA почти на границе."},
    {"name":"Ольга","vacancy":"Оператор","priority":"Высокий","stage":"Новый кандидат","delta":15,"answered":False,"next":"Ответить кандидату","blocker":"Нет ответа кандидату","comment":"Новый входящий. До SLA 15 минут."},
    {"name":"Сергей","vacancy":"Комплектовщик","priority":"Средний","stage":"Новый кандидат","delta":30,"answered":False,"next":"Ответить кандидату","blocker":"Нет ответа кандидату","comment":"Новый входящий. До SLA 30 минут."},
    {"name":"Ирина","vacancy":"Менеджер по продажам","priority":"Средний","stage":"Новый кандидат","delta":60,"answered":False,"next":"Ответить кандидату","blocker":"Нет ответа кандидату","comment":"Новый входящий. До SLA 1 часа."},

    {"name":"Артём","vacancy":"Водитель","priority":"Высокий","stage":"Квалификация","delta":-30,"answered":True,"next":"Написать кандидату","blocker":"Не отвечает","comment":"Кандидат не выходит на связь после первого контакта."},
    {"name":"Елена","vacancy":"Курьер","priority":"Средний","stage":"Квалификация","delta":-10,"answered":True,"next":"Позвонить кандидату","blocker":"Не отвечает","comment":"Нужно повторно связаться с кандидатом."},
    {"name":"Павел","vacancy":"Администратор","priority":"Средний","stage":"Квалификация","delta":20,"answered":True,"next":"Проверить квалификацию","blocker":"Не хватает данных","comment":"Нужно уточнить опыт и доступность."},
    {"name":"Анна","vacancy":"Кладовщик","priority":"Высокий","stage":"Квалификация","delta":45,"answered":True,"next":"Проверить квалификацию","blocker":"Не хватает данных","comment":"Нужно уточнить график и зарплатные ожидания."},

    {"name":"Максим","vacancy":"Водитель-экспедитор","priority":"Высокий","stage":"Интервью","delta":-20,"answered":True,"next":"Провести интервью","blocker":"Интервью сегодня","comment":"Время интервью уже наступило."},
    {"name":"Юлия","vacancy":"Администратор","priority":"Высокий","stage":"Интервью","delta":30,"answered":True,"next":"Провести интервью","blocker":"Интервью сегодня","comment":"Интервью запланировано в ближайшие 30 минут."},
    {"name":"Виктор","vacancy":"Менеджер по продажам","priority":"Средний","stage":"Интервью","delta":90,"answered":True,"next":"Подтвердить интервью","blocker":"Интервью сегодня","comment":"Нужно подтвердить время с кандидатом."},
    {"name":"Роман","vacancy":"Водитель","priority":"Средний","stage":"Интервью","delta":180,"answered":True,"next":"Провести интервью","blocker":"Интервью сегодня","comment":"Интервью запланировано на сегодня."},

    {"name":"Наталья","vacancy":"Кладовщик","priority":"Высокий","stage":"Документы","delta":-45,"answered":True,"next":"Запросить документы","blocker":"Документы не получены","comment":"Кандидат обещал прислать документы, срок уже прошёл."},
    {"name":"Александр","vacancy":"Комплектовщик","priority":"Высокий","stage":"Документы","delta":15,"answered":True,"next":"Проверить документы","blocker":"Ждём документы","comment":"Документы должны прийти в ближайшее время."},
    {"name":"Екатерина","vacancy":"Оператор","priority":"Средний","stage":"Документы","delta":60,"answered":True,"next":"Проверить документы","blocker":"Ждём документы","comment":"Кандидат собирает пакет документов."},
    {"name":"Андрей","vacancy":"Курьер","priority":"Низкий","stage":"Документы","delta":120,"answered":True,"next":"Проверить документы","blocker":"Ждём документы","comment":"Документы в работе у кандидата."},

    {"name":"Денис","vacancy":"Водитель","priority":"Высокий","stage":"Передан заказчику","delta":-30,"answered":True,"next":"Запросить обратную связь","blocker":"Нет ответа заказчика","comment":"Кандидат передан заказчику, обратная связь просрочена."},
    {"name":"Кирилл","vacancy":"Кладовщик","priority":"Высокий","stage":"Передан заказчику","delta":30,"answered":True,"next":"Запросить обратную связь","blocker":"Ждём заказчика","comment":"Нужно получить решение заказчика."},
    {"name":"Михаил","vacancy":"Курьер","priority":"Средний","stage":"Передан заказчику","delta":90,"answered":True,"next":"Проверить статус у заказчика","blocker":"Ждём заказчика","comment":"Кандидат на рассмотрении у заказчика."},
    {"name":"Илья","vacancy":"Оператор","priority":"Средний","stage":"Передан заказчику","delta":180,"answered":True,"next":"Проверить статус у заказчика","blocker":"Ждём заказчика","comment":"Нужно проконтролировать обратную связь."},

    {"name":"Николай","vacancy":"Водитель","priority":"Высокий","stage":"Выход на работу","delta":-20,"answered":True,"next":"Подтвердить выход","blocker":"Выход сегодня","comment":"Сегодня день выхода. Нужно подтвердить готовность."},
    {"name":"Павел","vacancy":"Кладовщик","priority":"Высокий","stage":"Выход на работу","delta":45,"answered":True,"next":"Подтвердить выход","blocker":"Выход сегодня","comment":"Выход запланирован на сегодня."},
    {"name":"Владислав","vacancy":"Комплектовщик","priority":"Средний","stage":"Выход на работу","delta":180,"answered":True,"next":"Напомнить кандидату","blocker":"Выход сегодня","comment":"Нужно подтвердить выход кандидата."},

    {"name":"Глеб","vacancy":"Администратор","priority":"Средний","stage":"Ожидаем решение","delta":-15,"answered":True,"next":"Запросить решение","blocker":"Нет решения","comment":"После интервью решение не получено в ожидаемый срок."},
    {"name":"Егор","vacancy":"Менеджер по продажам","priority":"Высокий","stage":"Ожидаем решение","delta":45,"answered":True,"next":"Запросить решение","blocker":"Нет решения","comment":"Нужно получить решение по кандидату."},
    {"name":"Степан","vacancy":"Водитель","priority":"Средний","stage":"Ожидаем решение","delta":120,"answered":True,"next":"Проверить статус","blocker":"Ждём решение","comment":"Решение ожидается сегодня."},
    {"name":"Тимур","vacancy":"Курьер","priority":"Низкий","stage":"Ожидаем решение","delta":240,"answered":True,"next":"Проверить статус","blocker":"Ждём решение","comment":"Кандидат на финальном согласовании."},
]


WORK_STAGES = [
    "Новый кандидат",
    "Квалификация",
    "Интервью",
    "Ожидаем решение",
    "Документы",
    "Передан заказчику",
    "Выход на работу",
]

# Расширенный демонстрационный набор: всего 50 кандидатов.

def call(method, params=None):
    response = requests.post(
        f"{WEBHOOK.rstrip('/')}/{method}.json",
        json=params or {},
        timeout=20,
    )
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError(
            f"Bitrix REST вернул не-JSON ответ (HTTP {response.status_code}): {response.text!r}"
        ) from error

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Bitrix REST вернул неожиданный ответ: {data!r} "
            f"(HTTP {response.status_code})"
        )

    if "error" in data:
        raise RuntimeError(
            f"{data['error']}: {data.get('error_description', '')}"
        )
    return data.get("result")


def get_pipeline():
    result = call("crm.category.list", {"entityTypeId": 2})
    categories = result.get("categories", []) if isinstance(result, dict) else []
    for category in categories:
        if category.get("name") == PIPELINE_NAME:
            return int(category["id"])
    raise RuntimeError(f"Не найдена воронка «{PIPELINE_NAME}».")


def get_stages(category_id):
    return call(
        "crm.status.list",
        {
            "filter": {"ENTITY_ID": f"DEAL_STAGE_{category_id}"},
            "order": {"SORT": "ASC"},
        },
    ) or []


def create_sla_candidate(category_id, user_id, stages, index):
    scenario = WORKDAY_SCENARIO[index]
    name = scenario["name"]
    vacancy = scenario["vacancy"]
    priority = scenario["priority"]
    deadline_delta = scenario["delta"]
    answered = scenario["answered"]
    scenario_stage = scenario["stage"]
    next_step = scenario["next"]
    blocker = scenario["blocker"]
    scenario_comment = scenario["comment"]

    # delta — только демо-смещение относительно текущего момента.
    # Источник SLA всё равно строится по правильной цепочке:
    # LAST_INBOUND_AT + SLA_MINUTES = RESPONSE_DEADLINE.
    now = datetime.now()
    inbound = now - timedelta(minutes=SLA_MINUTES - deadline_delta)
    deadline = inbound + timedelta(minutes=SLA_MINUTES)
    response = inbound + timedelta(minutes=35) if answered else None

    stage_name = scenario_stage
    stage_id = stages[stage_name]

    action_priority = urgency_level(deadline, now)

    fields = {
        DEAL_FIELD_CODES["CANDIDATE_FIRST_NAME"]: name,
        DEAL_FIELD_CODES["CANDIDATE_LAST_NAME"]: "Демо",
        DEAL_FIELD_CODES["CANDIDATE_PHONE"]: f"+7900{1000000 + index * 731}",
        DEAL_FIELD_CODES["DESIRED_POSITION"]: vacancy,
        DEAL_FIELD_CODES["VACANCY"]: vacancy,
        DEAL_FIELD_CODES["CANDIDATE_SOURCE"]: "StaffFlow Demo",
        DEAL_FIELD_CODES["LAST_INBOUND_AT"]: inbound.isoformat(timespec="seconds"),
        DEAL_FIELD_CODES["LAST_RESPONSE_AT"]: response.isoformat(timespec="seconds") if response else "",
        DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
        DEAL_FIELD_CODES["PRIORITY"]: priority,
        DEAL_FIELD_CODES["URGENCY"]: action_priority,
        DEAL_FIELD_CODES["BLOCKER"]: blocker,
        DEAL_FIELD_CODES["NEXT_STEP"]: next_step,
        # Для рабочего дня это время следующего действия.
        DEAL_FIELD_CODES["NEXT_ACTION_AT"]: deadline.isoformat(timespec="seconds"),
    }

    # Для первых шести кандидатов сначала создаём сделку вне «Новый кандидат».
    # Так демо-SLA записывается ДО входа в стадию, где срабатывает робот.
    create_stage_id = stages["Квалификация"] if stage_name == "Новый кандидат" else stage_id

    if stage_name == "Новый кандидат":
        # Для входящего кандидата не рисуем сделку через REST:
        # сообщение реально проходит Telegram → Connector → Open Channel → CRM.
        send_workday_incoming(name, vacancy, index)
        recent = find_recent_deal(category_id, name)
        deal_id = int(recent["id"])

        # Open Channel мог автоматически создать/привязать контакт.
        # Помечаем его тем же демо-маркером, чтобы «Удалить демо-день»
        # чистил и контакты, созданные реальным incoming-потоком.
        contact_ids = recent.get("contactIds", []) or []
        for contact_id in contact_ids:
            call(
                "crm.item.update",
                {
                    "entityTypeId": 3,
                    "id": int(contact_id),
                    "useOriginalUfNames": "Y",
                    "fields": {
                        "comments": "[DEMO] SLA simulator contact",
                    },
                },
            )

        # Open Channel уже создал сделку и запустил штатные роботы.
        # После этого накладываем демо-состояние рабочего дня поверх реального входящего.
        call(
            "crm.item.update",
            {
                "entityTypeId": 2,
                "id": deal_id,
                "useOriginalUfNames": "Y",
                "fields": {
                    "comments": DEMO_COMMENT,
                    DEAL_FIELD_CODES["CANDIDATE_FIRST_NAME"]: name,
                    DEAL_FIELD_CODES["DESIRED_POSITION"]: vacancy,
                    DEAL_FIELD_CODES["VACANCY"]: vacancy,
                    DEAL_FIELD_CODES["LAST_INBOUND_AT"]: inbound.isoformat(timespec="seconds"),
                    DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
                    DEAL_FIELD_CODES["NEXT_ACTION_AT"]: deadline.isoformat(timespec="seconds"),
                    DEAL_FIELD_CODES["PRIORITY"]: priority,
                    DEAL_FIELD_CODES["ACTION_PRIORITY"]: urgency_id,
                    DEAL_FIELD_CODES["BLOCKER"]: blocker,
                    DEAL_FIELD_CODES["NEXT_STEP"]: next_step,
                },
            },
        )
    else:
        deal = call(
            "crm.item.add",
            {
                "entityTypeId": 2,
                "useOriginalUfNames": "Y",
                "fields": {
                    "title": f"{name} — {vacancy}",
                    "categoryId": category_id,
                    "stageId": create_stage_id,
                    "assignedById": user_id,
                    "comments": DEMO_COMMENT,
                    **{k: v for k, v in fields.items() if k != DEAL_FIELD_CODES["CANDIDATE_SOURCE"]},
                },
            },
        )
        deal_id = int(deal["item"]["id"])

        # Сначала записываем демо-SLA в безопасной стадии, затем переводим в «Новый кандидат».
        call(
            "crm.item.update",
            {
                "entityTypeId": 2,
                "id": deal_id,
                "useOriginalUfNames": "Y",
                "fields": {
                    DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
                    DEAL_FIELD_CODES["NEXT_ACTION_AT"]: deadline.isoformat(timespec="seconds"),
                },
            },
        )

        
        call(
            "crm.item.update",
            {
                "entityTypeId": 2,
                "id": deal_id,
                "useOriginalUfNames": "Y",
                "fields": {"stageId": stage_id},
            },
        )
    time.sleep(2)


    call(
        "crm.timeline.comment.add",
        {
            "fields": {
                "ENTITY_ID": deal_id,
                "ENTITY_TYPE": "deal",
                "COMMENT": (
                    f"[WORKDAY DEMO] {scenario_comment}"
                ),
            }
        },
    )

    return deal_id, stage_name, priority, deadline_delta, answered


def create_pipeline_snapshot(category_id, user_id, stages, count=24):
    """Создаёт плотный рабочий срез по стадиям без имитации входящих."""
    candidates = WORKDAY_SCENARIO[6:]
    created = 0
    for i in range(min(count, len(candidates))):
        scenario = candidates[i]
        name = f"{scenario['name']} — Demo"
        # В срезе используем ту же SLA-модель:
        # LAST_INBOUND_AT + SLA_MINUTES = RESPONSE_DEADLINE.
        now = datetime.now()
        inbound = now - timedelta(minutes=SLA_MINUTES - scenario["delta"])
        deadline = inbound + timedelta(minutes=SLA_MINUTES)
        fields = {
            DEAL_FIELD_CODES["CANDIDATE_FIRST_NAME"]: name,
            DEAL_FIELD_CODES["CANDIDATE_LAST_NAME"]: "Демо",
            DEAL_FIELD_CODES["DESIRED_POSITION"]: scenario["vacancy"],
            DEAL_FIELD_CODES["VACANCY"]: scenario["vacancy"],
            DEAL_FIELD_CODES["PRIORITY"]: scenario["priority"],
            DEAL_FIELD_CODES["ACTION_PRIORITY"]: (
                urgency_level(deadline, now)
            ),
            DEAL_FIELD_CODES["BLOCKER"]: scenario["blocker"],
            DEAL_FIELD_CODES["NEXT_STEP"]: scenario["next"],
            DEAL_FIELD_CODES["LAST_INBOUND_AT"]: inbound.isoformat(timespec="seconds"),
            DEAL_FIELD_CODES["RESPONSE_DEADLINE"]: deadline.isoformat(timespec="seconds"),
            DEAL_FIELD_CODES["NEXT_ACTION_AT"]: deadline.isoformat(timespec="seconds"),
        }
        deal = call(
            "crm.item.add",
            {
                "entityTypeId": 2,
                "useOriginalUfNames": "Y",
                "fields": {
                    "title": name,
                    "categoryId": category_id,
                    "stageId": stages[scenario["stage"]],
                    "assignedById": user_id,
                    "comments": DEMO_COMMENT,
                    **fields,
                },
            },
        )
        deal_id = int(deal["item"]["id"])
        call(
            "crm.timeline.comment.add",
            {
                "fields": {
                    "ENTITY_ID": deal_id,
                    "ENTITY_TYPE": "deal",
                    "COMMENT": f"[WORKDAY SNAPSHOT] {scenario['comment']}",
                }
            },
        )
        created += 1
    return created


def delete_demo_tasks():
    deleted = 0
    data = call(
        "tasks.task.list",
        {
            "select": ["id", "title", "status"],
            "filter": {},
        },
    )
    tasks = (data or {}).get("tasks", [])
    for task in tasks:
        if task.get("title") == "Ответить кандидату":
            call("tasks.task.delete", {"taskId": int(task["id"])})
            deleted += 1
    return deleted


def delete_demo_contacts():
    deleted = 0
    while True:
        data = call(
            "crm.item.list",
            {
                "entityTypeId": 3,
                "select": ["id", "name", "lastName", "comments"],
                "filter": {"comments": "[DEMO] SLA simulator contact"},
            },
        )
        items = data.get("items", [])
        if not items:
            break
        for item in items:
            call(
                "crm.item.delete",
                {"entityTypeId": 3, "id": item["id"]},
            )
            deleted += 1
    return deleted


def tag_latest_health_check_deal(category_id):
    """Помечает сделку, созданную реальным incoming health-check."""
    data = call(
        "crm.item.list",
        {
            "entityTypeId": 2,
            "select": ["id", "comments", "title", "categoryId"],
            "filter": {"categoryId": category_id},
            "order": {"id": "DESC"},
        },
    )
    items = data.get("items", [])
    if not items:
        raise RuntimeError("Health-check создал сделку, но её не удалось найти в CRM.")

    deal_id = int(items[0]["id"])
    current_comments = str(items[0].get("comments", "") or "")
    marker = "[STAFFFLOW HEALTH CHECK]"
    comments = (
        current_comments
        if marker in current_comments
        else f"{current_comments}\n{marker}".strip()
    )
    if DEMO_COMMENT not in comments:
        comments = f"{comments}\n{DEMO_COMMENT}".strip()

    call(
        "crm.item.update",
        {
            "entityTypeId": 2,
            "id": deal_id,
            "fields": {"comments": comments},
        },
    )
    return deal_id


def clear_demo_unread_dialogs():
    """Сбрасывает unread-счётчик после тестовых incoming-сообщений."""
    call("im.dialog.read.all", {})
    return True


def delete_demo(category_id):
    total = 0

    while True:
        data = call(
            "crm.item.list",
            {
                "entityTypeId": 2,
                "select": ["id", "comments", "title", "contactIds"],
                "filter": {"categoryId": category_id},
            },
        )
        items = data.get("items", [])
        targets = [
            item for item in items
            if item.get("comments") == DEMO_COMMENT
            or str(item.get("title", "")).startswith("[DEMO]")
            or "SLA DEMO" in str(item.get("comments", ""))
            or "StaffFlow Health Check" in str(item.get("title", ""))
            or "Открытая линия" in str(item.get("title", ""))
        ]

        if not targets:
            break

        for item in targets:
            # Legacy incoming deals могли остаться без DEMO_COMMENT.
            # Перед удалением сделки сохраняем связанные контакты:
            # так чистим именно хвост Open Channel, а не все контакты CRM.
            for contact_id in item.get("contactIds", []) or []:
                try:
                    call(
                        "crm.item.delete",
                        {"entityTypeId": 3, "id": int(contact_id)},
                    )
                except Exception:
                    pass

            call(
                "crm.item.delete",
                {"entityTypeId": 2, "id": item["id"]},
            )
            total += 1

    return total


class App:
    def __init__(self, root):
        self.root = root
        root.title("StaffFlow — SLA Simulator")
        root.geometry("560x650")
        root.resizable(False, False)

        self.running = False
        self.thread = None
        self.pipeline_id = None
        self.user_id = None
        self.stages = {}
        self.scenario_index = 0
        self.created = 0

        frame = ttk.Frame(root, padding=22)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="STAFFFLOW — WORKDAY DEMO",
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(0, 8))

        ttk.Label(
            frame,
            text="Генератор создаёт реальные рабочие ситуации: SLA, звонки, интервью, документы и заказчик",
            font=("Segoe UI", 10),
        ).pack(pady=(0, 18))

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=5)
        ttk.Label(row, text="Интервал между сделками:").pack(side="left")
        self.interval = tk.IntVar(value=15)
        ttk.Entry(row, textvariable=self.interval, width=7).pack(side="left", padx=8)
        ttk.Label(row, text="секунд").pack(side="left")

        ttk.Separator(frame).pack(fill="x", pady=14)

        ttk.Label(
            frame,
            text="Рабочий день рекрутёра",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            frame,
            text=(
                "1–6: входящие и SLA\n"
                "7–30: квалификация → интервью → документы → заказчик → выход"
            ),
            justify="left",
        ).pack(anchor="w", pady=8)

        row = ttk.Frame(frame)
        row.pack(pady=12)

        ttk.Button(
            row,
            text="▶ ЗАПУСТИТЬ РАБОЧИЙ ДЕНЬ",
            command=self.start_scenario,
        ).pack(side="left", padx=5)

        ttk.Button(
            row,
            text="⏸ ПАУЗА",
            command=self.pause,
        ).pack(side="left", padx=5)

        ttk.Button(
            row,
            text="▶ СОЗДАТЬ СЛЕДУЮЩУЮ",
            command=self.create_next,
        ).pack(side="left", padx=5)

        ttk.Separator(frame).pack(fill="x", pady=8)

        ttk.Button(
            frame,
            text="СОЗДАТЬ СРЕЗ ВОРОНКИ (24 сделки)",
            command=self.create_pipeline_snapshot,
        ).pack(anchor="w", pady=5)
        ttk.Separator(frame).pack(fill="x", pady=14)

        ttk.Label(
            frame,
            text="Статус стенда",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")

        self.health_status = tk.StringVar(
            value="⚪ Не проверен"
        )
        ttk.Label(
            frame,
            textvariable=self.health_status,
            justify="left",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=6)

        ttk.Button(
            frame,
            text="🔍 ПРОВЕРИТЬ DEMO",
            command=self.health_check,
        ).pack(anchor="w", pady=(0, 10))

        ttk.Separator(frame).pack(fill="x", pady=10)

        ttk.Label(
            frame,
            text="Контроль стенда",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")

        row = ttk.Frame(frame)
        row.pack(pady=10)

        ttk.Button(
            row,
            text="🗑 УДАЛИТЬ ДЕМО-ДЕНЬ",
            command=self.delete_demo,
        ).pack(side="left", padx=5)

        ttk.Button(
            row,
            text="↻ СБРОСИТЬ СЦЕНАРИЙ",
            command=self.reset_scenario,
        ).pack(side="left", padx=5)

        self.status = tk.StringVar(value="Готов. Кандидатов в сценарии: 0 / 30")
        ttk.Label(
            frame,
            textvariable=self.status,
            font=("Segoe UI", 11),
        ).pack(pady=18)

        self.preview = tk.StringVar(
            value=(
                "Рабочий день:\n"
                "🔴 3 — просроченный SLA\n"
                "🟠 3 — SLA скоро истекает\n"
                "📞 4 — квалификация / нет ответа\n"
                "🎯 4 — интервью сегодня\n"
                "📄 4 — документы\n"
                "🤝 4 — ждём заказчика\n"
                "🚀 3 — выход на работу\n"
                "⏳ 4 — ждём решение"
            )
        )
        ttk.Label(
            frame,
            textvariable=self.preview,
            justify="left",
            font=("Consolas", 10),
        ).pack(anchor="w", pady=5)

    def ensure_ready(self):
        if self.pipeline_id is None:
            self.pipeline_id = get_pipeline()
        if self.user_id is None:
            self.user_id = get_current_user_id()
        if not self.stages:
            self.stages = stage_map(self.pipeline_id)

        missing = [x for x in WORK_STAGES if x not in self.stages]
        if missing:
            raise RuntimeError("Не найдены стадии: " + ", ".join(missing))

    def health_check(self):
        threading.Thread(target=self._health_check_worker, daemon=True).start()

    def _health_check_worker(self):
        results = []
        try:
            self.ensure_ready()
            results.append("🟢 Bitrix REST — OK")
        except Exception as error:
            results.append(f"🔴 Bitrix REST — {error}")

        try:
            check_connector()
            results.append("🟢 Connector /bitrix/app — OK")
        except Exception as error:
            results.append(f"🔴 Connector /bitrix/app — {error}")

        results.append(
            "🟡 Open Channel API status — проверяется не webhook'ом; "
            "реальная проверка ниже."
        )

        if CONNECTOR_TOKEN:
            try:
                before = count_pipeline_deals(self.pipeline_id)
                send_openline_test()
                after = wait_for_new_pipeline_deal(
                    self.pipeline_id,
                    before,
                    timeout=12,
                )
                if after > before:
                    # Health-check создаёт реальную CRM-сделку. Помечаем её
                    # тем же демо-маркером, чтобы кнопка очистки не оставляла
                    # после проверки «висячие» сделки.
                    tag_latest_health_check_deal(self.pipeline_id)
                    results.append(
                        f"🟢 Incoming → Open Channel → CRM — OK "
                        f"(сделок было {before}, стало {after})"
                    )
                else:
                    results.append(
                        "🔴 Incoming → CRM — сообщение отправлено connector'ом, "
                        "но новая CRM-сделка за 12 сек не появилась."
                    )
            except Exception as error:
                results.append(f"🔴 Incoming test — {error}")
        else:
            results.append(
                "🟡 Incoming test — не запущен: нет STAFFFLOW_SEND_TOKEN в .env"
            )

        text = "\n".join(results)
        self.root.after(0, lambda: self.health_status.set(text))

    def create_next(self):
        if self.running:
            return
        threading.Thread(target=self._create_next_worker, daemon=True).start()

    def _create_next_worker(self):
        try:
            self.ensure_ready()
            if self.scenario_index >= len(WORKDAY_SCENARIO):
                self.root.after(0, lambda: self.status.set("Сценарий завершён: 30 / 30"))
                return

            result = create_sla_candidate(
                self.pipeline_id,
                self.user_id,
                self.stages,
                self.scenario_index,
            )
            self.scenario_index += 1
            self.created += 1

            scenario = WORKDAY_SCENARIO[self.scenario_index - 1]
            name = scenario["name"]
            priority = scenario["priority"]
            delta = scenario["delta"]
            answered = scenario["answered"]
            if delta < 0:
                timing = f"просрочено на {abs(delta)} мин"
            elif answered:
                timing = "уже ответили"
            else:
                timing = f"осталось {delta} мин"

            self.root.after(
                0,
                lambda: self.status.set(
                    f"Создано {self.created} / {len(WORKDAY_SCENARIO)}: "
                    f"{name} — {priority} — {timing}"
                ),
            )
        except Exception as error:
            error_text = f"{type(error).__name__}: {error}\n\n{traceback.format_exc()}"
            self.root.after(0, lambda msg=error_text: messagebox.showerror("Ошибка", msg))

    def create_pipeline_snapshot(self):
        threading.Thread(target=self._create_pipeline_snapshot_worker, daemon=True).start()

    def _create_pipeline_snapshot_worker(self):
        try:
            self.ensure_ready()
            created = create_pipeline_snapshot(
                self.pipeline_id,
                self.user_id,
                self.stages,
                count=24,
            )
            self.root.after(
                0,
                lambda: self.status.set(
                    f"Создан срез воронки: {created} сделок по рабочим стадиям"
                ),
            )
        except Exception as error:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", repr(error)))

    def start_scenario(self):
        if self.running:
            return

        try:
            interval = max(int(self.interval.get()), 1)
        except ValueError:
            messagebox.showerror("Ошибка", "Интервал должен быть целым числом.")
            return

        if self.scenario_index >= len(WORKDAY_SCENARIO):
            messagebox.showinfo("Сценарий", "Сценарий уже завершён. Нажмите «Сбросить сценарий».")
            return

        self.running = True
        self.status.set("Сценарий запущен")
        self.thread = threading.Thread(
            target=self.loop,
            args=(interval,),
            daemon=True,
        )
        self.thread.start()

    def loop(self, interval):
        while self.running and self.scenario_index < len(WORKDAY_SCENARIO):
            self._create_next_worker()
            if self.running and self.scenario_index < len(WORKDAY_SCENARIO):
                time.sleep(interval)

        self.running = False
        self.root.after(
            0,
            lambda: self.status.set(
                f"Сценарий завершён: {self.created} / {len(WORKDAY_SCENARIO)}"
            ),
        )

    def pause(self):
        self.running = False
        self.status.set(f"Пауза: {self.created} / {len(WORKDAY_SCENARIO)}")

    def reset_scenario(self):
        self.pause()
        self.scenario_index = 0
        self.created = 0
        self.status.set("Сценарий сброшен: 0 / 30")

    def delete_demo(self):
        if not messagebox.askyesno(
            "Удалить SLA-демо",
            "Удалить сделки SLA DEMO из воронки «Подбор персонала»?",
        ):
            return

        try:
            self.pause()
            self.ensure_ready()
            deleted = delete_demo(self.pipeline_id)
            deleted_contacts = delete_demo_contacts()
            deleted_tasks = delete_demo_tasks()

            unread_status = "непрочитанные диалоги сброшены"
            try:
                clear_demo_unread_dialogs()
            except Exception as error:
                unread_status = f"непрочитанные диалоги НЕ сброшены: {error}"

            self.scenario_index = 0
            self.created = 0
            self.status.set(
                f"Удалено: сделки {deleted}, контакты {deleted_contacts}, "
                f"задачи «Ответить кандидату» {deleted_tasks}; "
                f"{unread_status}. Готово к новому запуску."
            )
        except Exception as error:
            messagebox.showerror(
                "Ошибка",
                f"{type(error).__name__}: {error}\n\n{traceback.format_exc()}",
            )


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
