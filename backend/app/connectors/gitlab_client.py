from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx


class GitLabNoteNotFoundError(Exception):
    pass


class GitLabClient:
    def __init__(self, *, base_url: str, token: str, timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {
            "PRIVATE-TOKEN": token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(
                method,
                f"{self.base_url}{path}",
                headers=self.headers,
                **kwargs,
            )
            response.raise_for_status()
            return response

    def test_connection(self) -> dict[str, Any]:
        response = self._request("GET", "/api/v4/user")
        data = response.json()
        return {
            "id": data.get("id"),
            "username": data.get("username"),
            "name": data.get("name"),
        }

    def parse_external_id(self, external_id: str) -> tuple[str, str]:
        if "!" not in external_id:
            raise ValueError(
                "GitLab external_id must be in format 'project_id!mr_iid' or 'group%2Fproject!mr_iid'"
            )

        project_id, mr_iid = external_id.split("!", 1)
        project_id = project_id.strip()
        mr_iid = mr_iid.strip()

        if not project_id or not mr_iid:
            raise ValueError("GitLab external_id is incomplete")

        return project_id, mr_iid

    def fetch_merge_request(self, project_id: str, mr_iid: str) -> dict[str, Any]:
        encoded_project = quote(project_id, safe="")
        response = self._request(
            "GET",
            f"/api/v4/projects/{encoded_project}/merge_requests/{mr_iid}",
        )
        return response.json()

    def create_note(self, project_id: str, mr_iid: str, body: str) -> str:
        encoded_project = quote(project_id, safe="")
        response = self._request(
            "POST",
            f"/api/v4/projects/{encoded_project}/merge_requests/{mr_iid}/notes",
            json={"body": body},
        )
        data = response.json()
        return str(data["id"])

    def update_note(self, project_id: str, mr_iid: str, note_id: str, body: str) -> None:
        encoded_project = quote(project_id, safe="")

        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(
                "PUT",
                f"{self.base_url}/api/v4/projects/{encoded_project}/merge_requests/{mr_iid}/notes/{note_id}",
                headers=self.headers,
                json={"body": body},
            )

        if response.status_code == 404:
            raise GitLabNoteNotFoundError(
                f"GitLab note '{note_id}' was not found for merge request '{project_id}!{mr_iid}'."
            )

        response.raise_for_status()

    def normalize_merge_request(
        self,
        mr_payload: dict[str, Any],
    ) -> tuple[str | None, str, dict[str, Any]]:
        title = mr_payload.get("title")
        description = mr_payload.get("description") or ""
        state = mr_payload.get("state")
        draft = mr_payload.get("draft")
        source_branch = mr_payload.get("source_branch")
        target_branch = mr_payload.get("target_branch")
        labels = mr_payload.get("labels") or []
        web_url = mr_payload.get("web_url")
        project_id = mr_payload.get("project_id")
        iid = mr_payload.get("iid")

        normalized_text = "\n".join(
            [
                f"Merge request: !{iid}" if iid is not None else "",
                f"Project id: {project_id}" if project_id is not None else "",
                f"Title: {title}" if title else "",
                f"State: {state}" if state else "",
                f"Draft: {draft}" if draft is not None else "",
                f"Source branch: {source_branch}" if source_branch else "",
                f"Target branch: {target_branch}" if target_branch else "",
                f"Labels: {', '.join(labels)}" if labels else "",
                "",
                "Description:",
                description or "(empty)",
            ]
        ).strip()

        metadata = {
            "project_id": project_id,
            "iid": iid,
            "state": state,
            "draft": draft,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "labels": labels,
            "web_url": web_url,
        }
        return title, normalized_text, metadata