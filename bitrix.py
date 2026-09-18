from __future__ import annotations

from typing import Any

import requests


class BitrixClient:
    def __init__(self, webhook: str, timeout: int = 30) -> None:
        self.webhook = webhook.rstrip("/")
        self.timeout = timeout

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.webhook}/{method}"
        response = requests.post(url, json=params or {}, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()

        if "error" in payload:
            raise RuntimeError(
                f"{method}: {payload.get('error')} — {payload.get('error_description', '')}"
            )

        return payload.get("result")

    def get_current_user(self) -> dict[str, Any]:
        return self.call("user.current")

    def list_users(self, limit: int = 50) -> list[dict[str, Any]]:
        result = self.call("user.get", {"FILTER": {}, "SORT": "ID", "ORDER": "ASC"})
        return (result or [])[:limit]

    def list_departments(self) -> list[dict[str, Any]]:
        result = self.call("department.get", {})
        return result or []

    def list_categories(self) -> list[dict[str, Any]]:
        result = self.call("crm.category.list", {"entityTypeId": 2})
        return (result or {}).get("categories", [])

    def add_category(self, name: str) -> int:
        result = self.call(
            "crm.category.add",
            {"entityTypeId": 2, "fields": {"name": name}},
        )
        return int(result["category"]["id"])

    def list_stages(self, category_id: int) -> list[dict[str, Any]]:
        entity_id = "DEAL_STAGE" if category_id == 0 else f"DEAL_STAGE_{category_id}"
        result = self.call(
            "crm.status.list",
            {"filter": {"ENTITY_ID": entity_id}, "order": {"SORT": "ASC"}},
        )
        return result or []

    def add_stage(
        self,
        category_id: int,
        name: str,
        status_id: str,
        sort: int,
        semantics: str = "process",
    ) -> Any:
        entity_id = "DEAL_STAGE" if category_id == 0 else f"DEAL_STAGE_{category_id}"
        return self.call(
            "crm.status.add",
            {
                "fields": {
                    "ENTITY_ID": entity_id,
                    "STATUS_ID": status_id,
                    "NAME": name,
                    "SORT": sort,
                    "SEMANTICS": semantics,
                }
            },
        )

    def add_department(self, name: str, parent: int = 0, head_id: int | None = None) -> int:
        fields: dict[str, Any] = {
            "NAME": name,
            "PARENT": parent,
        }
        if head_id is not None:
            fields["UF_HEAD"] = head_id
        result = self.call("department.add", fields)
        return int(result)

    def add_user(self, email: str, name: str, last_name: str, department_id: int) -> int:
        result = self.call(
            "user.add",
            {
                "EMAIL": email,
                "NAME": name,
                "LAST_NAME": last_name,
                "UF_DEPARTMENT": [department_id],
            },
        )
        return int(result)

    def add_deal(
        self,
        title: str,
        category_id: int,
        stage_id: str,
        assigned_by_id: int,
        comments: str = "",
    ) -> int:
        result = self.call(
            "crm.deal.add",
            {
                "fields": {
                    "TITLE": title,
                    "TYPE_ID": "COMPLEX",
                    "CATEGORY_ID": category_id,
                    "STAGE_ID": stage_id,
                    "ASSIGNED_BY_ID": assigned_by_id,
                    "OPENED": "Y",
                    "CLOSED": "N",
                    "COMMENTS": comments,
                }
            },
        )
        return int(result)
