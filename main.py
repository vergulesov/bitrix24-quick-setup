from __future__ import annotations

import sys

from bitrix import BitrixClient
from config import get_settings
from demo import run as run_demo
from setup import ensure_pipeline, setup


def make_client() -> BitrixClient:
    return BitrixClient(get_settings().webhook)


def check() -> None:
    client = make_client()
    me = client.get_current_user()
    print("REST OK")
    print(f"User: {me.get('NAME', '')} {me.get('LAST_NAME', '')}")
    print(f"ID: {me.get('ID')}")


def demo() -> None:
    client = make_client()
    me = client.get_current_user()
    pipeline_id = ensure_pipeline(client, "Подбор персонала")
    run_demo(client, pipeline_id, int(me["ID"]))


def usage() -> None:
    print("Usage: python main.py [check|setup|demo]")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "check":
        check()
    elif command == "setup":
        setup()
    elif command == "demo":
        demo()
    else:
        usage()
