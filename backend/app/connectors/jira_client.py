from __future__ import annotations

from typing import Any

import httpx


class JiraCommentNotFoundError(Exception):
    pass


class JiraClient:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        auth_type: str = "bearer",
        timeout: int = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auth_type = auth_type
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if auth_type == "basic":
            if ":" not in token:
                raise ValueError("Basic auth secret must be in format 'login:password'")
            username, password = token.split(":", 1)
            self._auth: tuple[str, str] | None = (username, password)
        else:
            self._auth = None
            self.headers["Authorization"] = f"Bearer {token}"

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        with httpx.Client(
            timeout=self.timeout,
            auth=self._auth,
            follow_redirects=False,
        ) as client:
            response = client.request(
                method,
                f"{self.base_url}{path}",
                headers=self.headers,
                **kwargs,
            )
            response.raise_for_status()
            return response

    def test_connection(self) -> dict[str, Any]:
        response = self._request("GET", "/rest/api/2/myself")
        data = response.json()
        return {
            "account_id": data.get("accountId"),
            "display_name": data.get("displayName"),
            "email": data.get("emailAddress"),
        }

    def fetch_issue(self, issue_key: str) -> dict[str, Any]:
        params = {"fields": "summary,description,status,issuetype,priority"}
        response = self._request(
            "GET",
            f"/rest/api/2/issue/{issue_key}",
            params=params,
        )
        return response.json()

    def create_comment(self, issue_key: str, body: str) -> str:
        payload = {"body": body}
        response = self._request(
            "POST",
            f"/rest/api/2/issue/{issue_key}/comment",
            json=payload,
        )
        data = response.json()
        return str(data["id"])

    def update_comment(self, issue_key: str, comment_id: str, body: str) -> None:
        payload = {"body": body}

        with httpx.Client(
            timeout=self.timeout,
            auth=self._auth,
            follow_redirects=False,
        ) as client:
            response = client.request(
                "PUT",
                f"{self.base_url}/rest/api/2/issue/{issue_key}/comment/{comment_id}",
                headers=self.headers,
                json=payload,
            )

        if response.status_code == 404:
            raise JiraCommentNotFoundError(
                f"Jira comment '{comment_id}' was not found for issue '{issue_key}'."
            )

        response.raise_for_status()

    def normalize_issue(
        self,
        issue_payload: dict[str, Any],
    ) -> tuple[str | None, str, dict[str, Any]]:
        fields = issue_payload.get("fields", {})
        title = fields.get("summary")
        description = self._adf_to_text(fields.get("description"))
        status_name = (fields.get("status") or {}).get("name")
        issue_type = (fields.get("issuetype") or {}).get("name")
        priority = (fields.get("priority") or {}).get("name")
        issue_key = issue_payload.get("key")
        issue_url = issue_payload.get("self")

        normalized_text = "\n".join(
            [
                f"Issue key: {issue_key}" if issue_key else "",
                f"Summary: {title}" if title else "",
                f"Status: {status_name}" if status_name else "",
                f"Issue type: {issue_type}" if issue_type else "",
                f"Priority: {priority}" if priority else "",
                "",
                "Description:",
                description or "(empty)",
            ]
        ).strip()

        metadata = {
            "issue_key": issue_key,
            "issue_url": issue_url,
            "status": status_name,
            "issue_type": issue_type,
            "priority": priority,
        }
        return title, normalized_text, metadata

    def _adf_to_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if not isinstance(value, dict):
            return str(value)

        parts: list[str] = []

        def walk(node: Any) -> None:
            if node is None:
                return
            if isinstance(node, str):
                parts.append(node)
                return
            if isinstance(node, list):
                for item in node:
                    walk(item)
                return
            if not isinstance(node, dict):
                parts.append(str(node))
                return

            node_type = node.get("type")
            if node_type in {"paragraph", "heading", "blockquote", "listItem"}:
                for item in node.get("content", []):
                    walk(item)
                parts.append("\n")
                return
            if node_type in {"bulletList", "orderedList", "doc"}:
                for item in node.get("content", []):
                    walk(item)
                return
            if node_type == "hardBreak":
                parts.append("\n")
                return
            if node_type == "text":
                parts.append(node.get("text", ""))
                return

            for item in node.get("content", []):
                walk(item)

        walk(value)
        text = "".join(parts)
        lines = [line.rstrip() for line in text.splitlines()]
        compact = [line for line in lines if line.strip()]
        return "\n".join(compact)