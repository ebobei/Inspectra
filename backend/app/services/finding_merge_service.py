import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.finding import Finding


class FindingMergeService:
    def merge(self, db: Session, *, session_id, review_run_id, llm_result: dict) -> list[Finding]:
        existing_findings = {
            f.finding_key: f
            for f in db.query(Finding).filter(Finding.review_session_id == session_id).all()
        }

        resolved_keys = set(
            str(item).strip()
            for item in llm_result.get("resolved_finding_keys", [])
            if str(item).strip()
        )
        still_open = llm_result.get("still_open_findings", []) or []
        new_findings = llm_result.get("new_findings", []) or []
        touched_open_keys = set()

        for finding_key in resolved_keys:
            if finding_key in existing_findings:
                item = existing_findings[finding_key]
                item.status = "resolved"
                item.resolution_type = "fixed_in_source"
                item.resolved_at = datetime.now(timezone.utc)
                item.last_seen_run_id = review_run_id

        for raw_payload in [*still_open, *new_findings]:
            payload = self._normalize_finding_payload(raw_payload)
            finding_key = payload["finding_key"]
            touched_open_keys.add(finding_key)
            existing = existing_findings.get(finding_key)
            if existing:
                existing.status = "open"
                existing.last_seen_run_id = review_run_id
                existing.title = payload["title"]
                existing.description = payload["description"]
                existing.category = payload["category"]
                existing.severity = payload["severity"]
                existing.times_repeated += 1
                existing.last_tone_level = payload["tone_level"]
                existing.resolved_at = None
                existing.resolution_type = None
            else:
                db.add(
                    Finding(
                        review_session_id=session_id,
                        first_detected_run_id=review_run_id,
                        last_seen_run_id=review_run_id,
                        finding_key=finding_key,
                        category=payload["category"],
                        severity=payload["severity"],
                        title=payload["title"],
                        description=payload["description"],
                        status="open",
                        times_repeated=0,
                        last_tone_level=payload["tone_level"],
                    )
                )

        for finding in existing_findings.values():
            if (
                finding.status == "open"
                and finding.finding_key not in touched_open_keys
                and finding.finding_key not in resolved_keys
            ):
                finding.status = "resolved"
                finding.resolution_type = "fixed_in_source"
                finding.resolved_at = datetime.now(timezone.utc)
                finding.last_seen_run_id = review_run_id

        db.flush()
        return db.query(Finding).filter(Finding.review_session_id == session_id).all()

    def _normalize_finding_payload(self, payload: Any) -> dict[str, str]:
        if not isinstance(payload, dict):
            payload = {}

        category = self._clean_text(payload.get("category"), default="general")
        severity = self._clean_text(payload.get("severity"), default="medium")
        title = self._clean_text(payload.get("title"), default="Review finding")
        description = self._clean_text(payload.get("description"), default=title)
        tone_level = self._clean_text(payload.get("tone_level"), default="neutral")
        finding_key = self._clean_text(payload.get("finding_key") or payload.get("key"), default="")

        if not finding_key:
            finding_key = self._build_finding_key(
                category=category,
                severity=severity,
                title=title,
                description=description,
            )

        return {
            "finding_key": finding_key,
            "category": category,
            "severity": severity,
            "title": title,
            "description": description,
            "tone_level": tone_level,
        }

    def _build_finding_key(
        self,
        *,
        category: str,
        severity: str,
        title: str,
        description: str,
    ) -> str:
        basis = "|".join(
            [
                category.strip().lower(),
                severity.strip().lower(),
                title.strip().lower(),
                description.strip().lower(),
            ]
        )
        digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]
        safe_category = re.sub(r"[^a-z0-9_-]+", "-", category.lower()).strip("-") or "general"
        return f"{safe_category}:{digest}"

    def _clean_text(self, value: Any, *, default: str) -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default
