from __future__ import annotations

import argparse
from typing import Any

from bitrix import BitrixClient


DEAL_ID = 419
CONTACT_NAME = "Никита"
CONTACT_PHONE = "+79090812390"
CONTACT_TELEGRAM = "@vergelesn"
CHAT_TITLE = "Никита — Открытая линия"


def find_openline_chat(client: BitrixClient) -> dict[str, Any]:
    """
    Находим чат через CRM-привязку, без im.recent.list.
    Текущий тестовый контакт виден в UI как contact/3, а если
    привязки к контакту нет — пробуем тестовую сделку 419.
    """
    # 1. Ищем контакт по телефону и проверяем связанные Open Line чаты.
    contact = find_contact(client)
    if contact:
        contact_id = int(contact["ID"])
        print(f"Contact {contact_id} raw IM: {contact.get('IM')}")
        print(f"Contact {contact_id} raw data: {contact}")
        result = client.call(
            "imopenlines.crm.chat.get",
            {
                "CRM_ENTITY_TYPE": "contact",
                "CRM_ENTITY": contact_id,
                "ACTIVE_ONLY": "N",
            },
        )
        chats = result or []
        if chats:
            chat = chats[-1]
            print(
                f"Найден чат через контакт {contact_id}: "
                f"CHAT_ID={chat.get('CHAT_ID')} | "
                f"{chat.get('CONNECTOR_TITLE')}"
            )
            return {
                "chat_id": int(chat["CHAT_ID"]),
                "title": CHAT_TITLE,
            }

    # 2. На всякий случай проверяем тестовую сделку.
    result = client.call(
        "imopenlines.crm.chat.get",
        {
            "CRM_ENTITY_TYPE": "deal",
            "CRM_ENTITY": DEAL_ID,
            "ACTIVE_ONLY": "N",
        },
    )
    chats = result or []
    if chats:
        chat = chats[-1]
        print(
            f"Найден чат через сделку {DEAL_ID}: "
            f"CHAT_ID={chat.get('CHAT_ID')} | "
            f"{chat.get('CONNECTOR_TITLE')}"
        )
        return {
            "chat_id": int(chat["CHAT_ID"]),
            "title": CHAT_TITLE,
        }

    probe_openline_session(client)
    raise RuntimeError(
        "Open Line чат не найден через CRM-привязки. "
        "Диагностика session.open выполнена выше."
    )

def probe_openline_session(client: BitrixClient) -> None:
    """
    Диагностика: пробуем получить/открыть сессию Open Line.
    Ничего в CRM не изменяем.
    """
    user_codes = [
        "telegram|1|StaffFlow_Test_Bot|vergelesn",
        "telegram|1|StaffFlow_Test_Bot|79090812390",
        "telegram|1|StaffFlow_Test_Bot|+79090812390",
    ]

    for user_code in user_codes:
        print(f"\nПробуем USER_CODE: {user_code}")
        try:
            result = client.call(
                "imopenlines.session.open",
                {"USER_CODE": user_code},
            )
            print(f"session.open RESULT: {result}")
        except Exception as exc:
            print(f"session.open ERROR: {exc}")



def get_dialog(client: BitrixClient, chat_id: int) -> dict[str, Any]:
    return client.call("imopenlines.dialog.get", {"CHAT_ID": chat_id})


def get_history(client: BitrixClient, chat_id: int) -> dict[str, Any]:
    return client.call(
        "imopenlines.session.history.get",
        {"CHAT_ID": chat_id},
    )


def find_contact(client: BitrixClient) -> dict[str, Any] | None:
    result = client.call(
        "crm.contact.list",
        {
            "filter": {"PHONE": CONTACT_PHONE},
            "select": ["ID", "NAME", "LAST_NAME", "PHONE", "IM"],
            "order": {"ID": "ASC"},
        },
    )
    contacts = result or []
    return contacts[0] if contacts else None


def create_contact(client: BitrixClient, imol: str) -> int:
    result = client.call(
        "crm.item.add",
        {
            "entityTypeId": 3,
            "fields": {
                "name": CONTACT_NAME,
                "lastName": "Тестовый",
                "fm": [
                    {
                        "typeId": "PHONE",
                        "valueType": "MOBILE",
                        "value": CONTACT_PHONE,
                    },
                    {
                        "typeId": "IM",
                        "valueType": "OTHER",
                        "value": imol,
                    },
                ],
            },
        },
    )
    return int(result["item"]["id"])


def ensure_contact(client: BitrixClient, imol: str) -> int:
    existing = find_contact(client)
    if existing:
        contact_id = int(existing["ID"])
        print(f"Contact exists: {contact_id}")
        return contact_id

    contact_id = create_contact(client, imol)
    print(f"Contact created: {contact_id}")
    return contact_id


def ensure_deal_contact(client: BitrixClient, deal_id: int, contact_id: int) -> None:
    deal = client.call(
        "crm.item.get",
        {"entityTypeId": 2, "id": deal_id},
    )["item"]
    current = [int(value) for value in (deal.get("contactIds") or [])]

    if contact_id in current:
        print(f"Deal {deal_id}: contact {contact_id} already linked")
        return

    client.call(
        "crm.item.update",
        {
            "entityTypeId": 2,
            "id": deal_id,
            "fields": {
                "contactIds": current + [contact_id],
            },
        },
    )
    print(f"Deal {deal_id}: linked contact {contact_id}")


def restore_timeline(
    client: BitrixClient,
    deal_id: int,
    history: dict[str, Any],
) -> None:
    messages = history.get("message", {})
    ordered = sorted(
        messages.values(),
        key=lambda item: (item.get("date") or "", int(item.get("id", 0))),
    )

    lines: list[str] = []
    for item in ordered:
        text = str(item.get("textlegacy") or item.get("text") or "").strip()
        if not text:
            continue
        date = item.get("date", "")
        sender = item.get("senderid", "?")
        lines.append(f"[{date}] {sender}: {text}")

    if not lines:
        print("History is empty; timeline restore skipped")
        return

    comment = "Восстановленная история Open Line через REST:\n" + "\n".join(lines)
    client.call(
        "crm.timeline.comment.add",
        {
            "fields": {
                "ENTITY_ID": deal_id,
                "ENTITY_TYPE": "deal",
                "COMMENT": comment,
            }
        },
    )
    print(f"Timeline restored: {len(lines)} messages")


def try_rebind_session(client: BitrixClient, chat_id: int) -> None:
    before = get_dialog(client, chat_id)
    print(f"Before entity_data_2: {before.get('entity_data_2')}")

    try:
        result = client.call("imopenlines.session.start", {"CHAT_ID": chat_id})
        print(f"Session restarted: {result}")
    except Exception as exc:
        print(f"Session restart skipped: {exc}")

    after = get_dialog(client, chat_id)
    print(f"After entity_data_2:  {after.get('entity_data_2')}")

    if before.get("entity_data_2") != after.get("entity_data_2"):
        print("CRM binding changed after session restart.")
    else:
        print(
            "CRM binding did not change. REST has no documented public method "
            "to directly overwrite entity_data_2; stopping here."
        )


def run(client: BitrixClient, deal_id: int = DEAL_ID, restore_history: bool = True) -> None:
    chat = find_openline_chat(client)
    chat_id = int(chat["chat_id"])
    print(f"Open Line chat: {chat.get('title')} | CHAT_ID={chat_id}")

    dialog = get_dialog(client, chat_id)
    entity_id = str(dialog.get("entity_id") or "")
    if not entity_id:
        raise RuntimeError("Open Line dialog has empty entity_id")

    print(f"entity_id: {entity_id}")
    print(f"entity_data_2: {dialog.get('entity_data_2')}")

    imol = f"imol|{entity_id}"
    print(f"CRM messenger key: {imol}")

    contact_id = ensure_contact(client, imol)
    ensure_deal_contact(client, deal_id, contact_id)

    history = get_history(client, chat_id)
    if restore_history:
        restore_timeline(client, deal_id, history)

    try_rebind_session(client, chat_id)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Восстановление тестового Telegram/Open Line клиента через Bitrix REST"
    )
    parser.add_argument("--deal-id", type=int, default=DEAL_ID)
    parser.add_argument("--no-history", action="store_true")
    args = parser.parse_args()

    from config import get_settings

    client = BitrixClient(get_settings().webhook)
    run(client, deal_id=args.deal_id, restore_history=not args.no_history)


if __name__ == "__main__":
    main()
