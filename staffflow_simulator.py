import os
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

from schema import DEAL_FIELD_CODES

load_dotenv()

WEBHOOK = os.getenv("BITRIX_WEBHOOK_URL") or os.getenv("BITRIX_WEBHOOK")
if not WEBHOOK:
    raise SystemExit("Не найден BITRIX_WEBHOOK_URL / BITRIX_WEBHOOK в .env")

PIPELINE_NAME = "Подбор персонала"
DEMO_COMMENT = "SLA DEMO DATA"

SLA_SCENARIO = [
    # name, vacancy, priority, minutes_to_deadline, answered
    ("Алексей", "Водитель", "Высокий", -95, False),
    ("Марина", "Кладовщик", "Высокий", -35, False),
    ("Дмитрий", "Курьер", "Средний", 25, False),
    ("Ольга", "Оператор", "Высокий", 70, False),
    ("Сергей", "Комплектовщик", "Низкий", 115, False),
    ("Ирина", "Менеджер по продажам", "Средний", 180, True),

    ("Артём", "Водитель", "Высокий", 45, True),
    ("Елена", "Курьер", "Средний", 120, True),
    ("Пётр", "Оператор", "Низкий", 240, True),
    ("Анна", "Кладовщик", "Высокий", 30, True),
    ("Максим", "Водитель-экспедитор", "Средний", 90, True),
    ("Юлия", "Администратор", "Низкий", 210, True),

    ("Виктор", "Менеджер по продажам", "Высокий", 60, True),
    ("Роман", "Водитель", "Средний", 150, True),
    ("Наталья", "Кладовщик", "Высокий", 75, True),
    ("Александр", "Комплектовщик", "Средний", 300, True),
    ("Екатерина", "Оператор", "Высокий", 40, True),
    ("Андрей", "Курьер", "Средний", 360, True),
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


def call(method, params=None):
    response = requests.post(
        f"{WEBHOOK.rstrip('/')}/{method}.json",
        json=params or {},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
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


def get_current_user_id():
    return int(call("user.current")["ID"])


def stage_map(category_id):
    return {
        item["NAME"]: item["STATUS_ID"]
        for item in get_stages(category_id)
        if item.get("NAME")
    }


def create_sla_candidate(category_id, user_id, stages, index):
    name, vacancy, priority, deadline_delta, answered = SLA_SCENARIO[index]

    now = datetime.now(timezone.utc)
    deadline = now + timedelta(minutes=deadline_delta)
    inbound = deadline - timedelta(hours=2)
    response = inbound + timedelta(minutes=35) if answered else None

    # Первые 6 — именно SLA-очередь. Остальные распределяются по рабочим стадиям.
    stage_name = "Новый кандидат" if index < 6 else WORK_STAGES[1 + ((index - 6) % (len(WORK_STAGES) - 1))]
    stage_id = stages[stage_name]

    contact = call(
        "crm.item.add",
        {
            "entityTypeId": 3,
            "fields": {
                "name": name,
                "lastName": "Демо",
                "fm": [
                    {
                        "typeId": "PHONE",
                        "valueType": "WORK",
                        "value": f"+7900{1000000 + index * 731}",
                    },
                    {
                        "typeId": "EMAIL",
                        "valueType": "WORK",
                        "value": f"sla{index + 1}@staffflow.test",
                    },
                ],
                "assignedById": user_id,
                "comments": "[DEMO] SLA simulator contact",
            },
        },
    )
    contact_id = int(contact["item"]["id"])

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
        DEAL_FIELD_CODES["BLOCKER"]: "Не ответил кандидату" if not answered else "В работе",
        DEAL_FIELD_CODES["NEXT_STEP"]: "Ответить кандидату" if not answered else "Следующий шаг",
        DEAL_FIELD_CODES["NEXT_ACTION_AT"]: (
            (now + timedelta(minutes=max(10, deadline_delta))).isoformat(timespec="seconds")
        ),
    }

    deal = call(
        "crm.item.add",
        {
            "entityTypeId": 2,
            "fields": {
                "title": f"{name} — {vacancy}",
                "categoryId": category_id,
                "stageId": stage_id,
                "assignedById": user_id,
                "contactIds": [contact_id],
                "comments": DEMO_COMMENT,
                **fields,
            },
        },
    )
    deal_id = int(deal["item"]["id"])

    # Робот мог поставить стандартные +2 часа. Для демонстрации SLA
    # сразу задаём контролируемое состояние: просрочено / 25 мин / 70 мин и т.д.
    call(
        "crm.item.update",
        {
            "entityTypeId": 2,
            "id": deal_id,
            "fields": fields,
        },
    )

    call(
        "crm.timeline.comment.add",
        {
            "fields": {
                "ENTITY_ID": deal_id,
                "ENTITY_TYPE": "deal",
                "COMMENT": (
                    f"[SLA DEMO] Входящий контакт: кандидат спрашивает про «{vacancy}»."
                    + (" Рекрутер ответил." if answered else " Ответ не отправлен.")
                ),
            }
        },
    )

    return deal_id, stage_name, priority, deadline_delta, answered


def delete_demo(category_id):
    total = 0

    while True:
        data = call(
            "crm.item.list",
            {
                "entityTypeId": 2,
                "select": ["id", "comments", "title"],
                "filter": {"categoryId": category_id},
            },
        )
        items = data.get("items", [])
        targets = [
            item for item in items
            if item.get("comments") == DEMO_COMMENT
            or str(item.get("title", "")).startswith("[DEMO]")
            or "SLA DEMO" in str(item.get("comments", ""))
        ]

        if not targets:
            break

        for item in targets:
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
        root.geometry("560x500")
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
            text="STAFFFLOW — SLA DEMO",
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(0, 8))

        ttk.Label(
            frame,
            text="Генератор создаёт кандидатов по заранее заданному сюжету",
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
            text="Сценарий SLA",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            frame,
            text=(
                "1–6: очередь ответа\n"
                "7–18: квалификация → интервью → решение → документы → клиент → выход"
            ),
            justify="left",
        ).pack(anchor="w", pady=8)

        row = ttk.Frame(frame)
        row.pack(pady=12)

        ttk.Button(
            row,
            text="▶ ЗАПУСТИТЬ СЦЕНАРИЙ",
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

        ttk.Separator(frame).pack(fill="x", pady=14)

        ttk.Label(
            frame,
            text="Контроль стенда",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")

        row = ttk.Frame(frame)
        row.pack(pady=10)

        ttk.Button(
            row,
            text="🗑 УДАЛИТЬ SLA-ДЕМО",
            command=self.delete_demo,
        ).pack(side="left", padx=5)

        ttk.Button(
            row,
            text="СБРОСИТЬ СЦЕНАРИЙ",
            command=self.reset_scenario,
        ).pack(side="left", padx=5)

        self.status = tk.StringVar(value="Готов. Сделок в сценарии: 0 / 18")
        ttk.Label(
            frame,
            textvariable=self.status,
            font=("Segoe UI", 11),
        ).pack(pady=18)

        self.preview = tk.StringVar(
            value=(
                "Первые 6:\n"
                "🔴 Алексей — Высокий — просрочено\n"
                "🔴 Марина — Высокий — просрочено\n"
                "🟠 Дмитрий — Средний — 25 мин\n"
                "🟡 Ольга — Высокий — 70 мин\n"
                "🟡 Сергей — Низкий — 115 мин\n"
                "🟢 Ирина — Средний — уже ответили"
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

    def create_next(self):
        if self.running:
            return
        threading.Thread(target=self._create_next_worker, daemon=True).start()

    def _create_next_worker(self):
        try:
            self.ensure_ready()
            if self.scenario_index >= len(SLA_SCENARIO):
                self.root.after(0, lambda: self.status.set("Сценарий завершён: 18 / 18"))
                return

            result = create_sla_candidate(
                self.pipeline_id,
                self.user_id,
                self.stages,
                self.scenario_index,
            )
            self.scenario_index += 1
            self.created += 1

            name, vacancy, priority, delta, answered = SLA_SCENARIO[self.scenario_index - 1]
            if delta < 0:
                timing = f"просрочено на {abs(delta)} мин"
            elif answered:
                timing = "уже ответили"
            else:
                timing = f"осталось {delta} мин"

            self.root.after(
                0,
                lambda: self.status.set(
                    f"Создано {self.created} / {len(SLA_SCENARIO)}: "
                    f"{name} — {priority} — {timing}"
                ),
            )
        except Exception as error:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(error)))

    def start_scenario(self):
        if self.running:
            return

        try:
            interval = max(int(self.interval.get()), 1)
        except ValueError:
            messagebox.showerror("Ошибка", "Интервал должен быть целым числом.")
            return

        if self.scenario_index >= len(SLA_SCENARIO):
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
        while self.running and self.scenario_index < len(SLA_SCENARIO):
            self._create_next_worker()
            if self.running and self.scenario_index < len(SLA_SCENARIO):
                time.sleep(interval)

        self.running = False
        self.root.after(
            0,
            lambda: self.status.set(
                f"Сценарий завершён: {self.created} / {len(SLA_SCENARIO)}"
            ),
        )

    def pause(self):
        self.running = False
        self.status.set(f"Пауза: {self.created} / {len(SLA_SCENARIO)}")

    def reset_scenario(self):
        self.pause()
        self.scenario_index = 0
        self.created = 0
        self.status.set("Сценарий сброшен: 0 / 18")

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
            self.scenario_index = 0
            self.created = 0
            self.status.set(f"Удалено SLA-демо: {deleted}. Готово к новому запуску.")
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
