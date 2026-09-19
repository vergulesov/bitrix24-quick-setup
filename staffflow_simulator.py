import os
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import requests
from dotenv import load_dotenv

load_dotenv()

WEBHOOK = os.getenv("BITRIX_WEBHOOK_URL") or os.getenv("BITRIX_WEBHOOK")
if not WEBHOOK:
    raise SystemExit("Не найден BITRIX_WEBHOOK_URL / BITRIX_WEBHOOK в .env")

PIPELINE_NAME = "Подбор персонала"

NAMES = [
    "Алексей Смирнов", "Марина Фёдорова", "Ирина Лебедева",
    "Ольга Кузнецова", "Артём Васильев", "Пётр Кузнецов",
    "Елена Морозова", "Дмитрий Волков", "Анна Соколова",
    "Сергей Орлов", "Юлия Попова", "Максим Власов",
]
POSITIONS = [
    "Менеджер по продажам", "Кладовщик", "Водитель",
    "Оператор", "Комплектовщик", "Курьер",
    "Водитель-экспедитор", "Менеджер по работе с клиентами",
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
    entity_id = f"DEAL_STAGE_{category_id}"
    return call(
        "crm.status.list",
        {
            "filter": {"ENTITY_ID": entity_id},
            "order": {"SORT": "ASC"},
        },
    ) or []


def get_new_stage(category_id):
    for stage in get_stages(category_id):
        if stage.get("NAME") == "Новый кандидат":
            return stage.get("STATUS_ID")
    raise RuntimeError(
        f"Не найдена стадия «Новый кандидат» в воронке «{PIPELINE_NAME}»."
    )


def get_current_user_id():
    user = call("user.current")
    return int(user["ID"])


def create_candidate(category_id, stage_id, responsible_id, stage_path):
    name = random.choice(NAMES)
    position = random.choice(POSITIONS)

    contact = call(
        "crm.item.add",
        {
            "entityTypeId": 3,
            "fields": {
                "name": name.split()[0],
                "lastName": name.split()[-1],
                "fm": [
                    {
                        "typeId": "PHONE",
                        "valueType": "WORK",
                        "value": f"+7900{random.randint(1000000, 9999999)}",
                    },
                    {
                        "typeId": "EMAIL",
                        "valueType": "WORK",
                        "value": f"demo{random.randint(100000000, 999999999)}@staffflow.test",
                    },
                ],
                "assignedById": responsible_id,
                "comments": "[DEMO] Контакт создан симулятором.",
            },
        },
    )
    contact_id = int(contact["item"]["id"])

    title = f"[DEMO] {name} — {position}"
    deal = call(
        "crm.item.add",
        {
            "entityTypeId": 2,
            "fields": {
                "title": title,
                "categoryId": category_id,
                "stageId": stage_id,
                "assignedById": responsible_id,
                "contactIds": [contact_id],
            },
        },
    )
    deal_id = int(deal["item"]["id"])

    # Прогоняем сделку по предыдущим этапам, чтобы в CRM был виден путь.
    for target_stage_id in stage_path:
        if target_stage_id == stage_id:
            continue
        call(
            "crm.item.update",
            {
                "entityTypeId": 2,
                "id": deal_id,
                "fields": {"stageId": target_stage_id},
            },
        )
        time.sleep(0.15)

    # Входящее оставляем только у текущего кандидата на финальном этапе пути.
    if stage_path and stage_path[-1] == stage_id:
        add_incoming_activity(
            deal_id=deal_id,
            contact_id=contact_id,
            responsible_id=responsible_id,
        )

    return deal_id, contact_id


def add_incoming_activity(deal_id, contact_id, responsible_id):
    """
    Создаёт незавершённое входящее CRM-дело.
    Это имитация входящего события для очереди CRM:
    оно должно попадать во «Входящие»/Activities view.

    Важно: это не настоящий чат Open Channel и не создаёт сообщение
    в Telegram/WhatsApp. Реальный E2E-канал остаётся отдельным тестом.
    """
    call(
        "crm.activity.add",
        {
            "fields": {
                "OWNER_ID": deal_id,
                "OWNER_TYPE_ID": 2,
                "TYPE_ID": 6,
                "PROVIDER_ID": "CRM_EXTERNAL_CHANNEL",
                "PROVIDER_TYPE_ID": "ACTIVITY",
                "COMMUNICATIONS": [
                    {
                        "VALUE": f"demo-{contact_id}@staffflow.test",
                        "ENTITY_ID": contact_id,
                        "ENTITY_TYPE_ID": 3,
                    }
                ],
                "SUBJECT": "Входящее сообщение — [DEMO]",
                "DESCRIPTION": "Кандидат написал. Требуется ответ.",
                "DESCRIPTION_TYPE": 1,
                "COMPLETED": "N",
                "RESPONSIBLE_ID": responsible_id,
                "DIRECTION": 1,
                "IS_INCOMING_CHANNEL": "Y",
                "START_TIME": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        },
    )


def delete_demo(category_id):
    total = 0
    start = 0

    while True:
        data = call(
            "crm.item.list",
            {
                "entityTypeId": 2,
                "select": ["id", "title"],
                "filter": {"categoryId": category_id},
                "start": start,
            },
        )
        items = data.get("items", [])

        if not items:
            break

        for item in items:
            if str(item.get("title", "")).startswith("[DEMO] "):
                call(
                    "crm.item.delete",
                    {
                        "entityTypeId": 2,
                        "id": item["id"],
                    },
                )
                total += 1

        if not data.get("next"):
            break
        start = data["next"]

    # Удаляем связанные демо-контакты отдельно, чтобы не оставлять мусор.
    start = 0
    while True:
        data = call(
            "crm.item.list",
            {
                "entityTypeId": 3,
                "select": ["id", "name", "lastName", "comments"],
                "filter": {},
                "start": start,
            },
        )
        items = data.get("items", [])
        if not items:
            break

        for item in items:
            if "[DEMO]" in str(item.get("comments", "")):
                call(
                    "crm.item.delete",
                    {
                        "entityTypeId": 3,
                        "id": item["id"],
                    },
                )

        if not data.get("next"):
            break
        start = data["next"]

    return total


class App:
    def __init__(self, root):
        self.root = root
        root.title("StaffFlow Simulator")
        root.geometry("420x330")
        root.resizable(False, False)

        self.running = False
        self.thread = None
        self.created = 0
        self.pipeline_id = None
        self.stage_id = None
        self.responsible_id = None
        self.stage_ids = []

        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="STAFFFLOW SIMULATOR",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(0, 20))

        row = ttk.Frame(frame)
        row.pack(fill="x")
        ttk.Label(row, text="Скорость:").pack(side="left")

        self.speed = tk.IntVar(value=60)
        ttk.Entry(row, textvariable=self.speed, width=8).pack(
            side="left", padx=8
        )
        ttk.Label(row, text="кандидатов / час").pack(side="left")

        row = ttk.Frame(frame)
        row.pack(pady=18)

        ttk.Button(
            row, text="▶ СТАРТ", command=self.start
        ).pack(side="left", padx=5)
        ttk.Button(
            row, text="⏸ ПАУЗА", command=self.pause
        ).pack(side="left", padx=5)

        ttk.Separator(frame).pack(fill="x", pady=5)

        ttk.Label(frame, text="Создать сейчас").pack(pady=(10, 5))

        row = ttk.Frame(frame)
        row.pack()

        for count in (1, 5, 10):
            ttk.Button(
                row,
                text=str(count),
                command=lambda value=count: self.create_now(value),
            ).pack(side="left", padx=4)

        self.status = tk.StringVar(value="Готов")
        ttk.Label(frame, textvariable=self.status).pack(pady=15)

        ttk.Button(
            frame,
            text="🗑 УДАЛИТЬ ДЕМО-ДАННЫЕ",
            command=self.delete_demo,
        ).pack(pady=5)

    def ensure_stage(self):
        if self.pipeline_id is None:
            self.pipeline_id = get_pipeline()
        if self.stage_id is None:
            self.stage_id = get_new_stage(self.pipeline_id)
        if self.responsible_id is None:
            self.responsible_id = get_current_user_id()
        if not self.stage_ids:
            self.stage_ids = [
                s.get("STATUS_ID")
                for s in get_stages(self.pipeline_id)
                if s.get("NAME") in {
                    "Новый кандидат",
                    "Квалификация",
                    "Интервью",
                    "Ожидаем решение",
                    "Документы",
                    "Передан заказчику",
                    "Выход на работу",
                    "Отказ",
                }
            ]

    def create_now(self, count):
        def work():
            try:
                self.ensure_stage()
                for _ in range(count):
                    current_index = random.randrange(len(self.stage_ids))
                    current_stage = self.stage_ids[current_index]
                    path = self.stage_ids[: current_index + 1]
                    create_candidate(
                        self.pipeline_id,
                        current_stage,
                        self.responsible_id,
                        path,
                    )
                    self.created += 1

                self.root.after(
                    0,
                    lambda: self.status.set(
                        f"Создано: {self.created}"
                    ),
                )
            except Exception as error:
                self.root.after(
                    0,
                    lambda: messagebox.showerror("Ошибка", str(error)),
                )

        threading.Thread(target=work, daemon=True).start()

    def start(self):
        if self.running:
            return

        try:
            speed = float(self.speed.get())
            if speed <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Ошибка",
                "Скорость должна быть положительным числом.",
            )
            return

        self.running = True
        self.status.set("Симуляция запущена")
        self.thread = threading.Thread(
            target=self.loop,
            daemon=True,
        )
        self.thread.start()

    def loop(self):
        while self.running:
            try:
                self.ensure_stage()
                create_candidate(
                    self.pipeline_id,
                    self.stage_id,
                    self.responsible_id,
                )
                self.created += 1

                self.root.after(
                    0,
                    lambda: self.status.set(
                        f"Симуляция: создано {self.created}"
                    ),
                )

                speed = max(float(self.speed.get()), 0.1)
                time.sleep(3600 / speed)

            except Exception as error:
                self.running = False
                self.root.after(
                    0,
                    lambda: messagebox.showerror("Ошибка", str(error)),
                )
                break

    def pause(self):
        self.running = False
        self.status.set("Пауза")

    def delete_demo(self):
        if not messagebox.askyesno(
            "Удалить демо",
            "Удалить только сделки с префиксом [DEMO]?",
        ):
            return

        try:
            self.pause()
            self.ensure_stage()
            deleted = delete_demo(self.pipeline_id)
            self.status.set(f"Удалено демо-сделок: {deleted}")
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
