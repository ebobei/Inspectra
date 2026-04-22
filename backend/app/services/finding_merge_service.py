from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.finding import Finding


class FindingMergeService:
    def merge(self, db: Session, *, session_id, review_run_id, llm_result: dict) -> list[Finding]:
        existing_findings = {
            f.finding_key: f
            for f in db.query(Finding).filter(Finding.review_session_id == session_id).all()
        }

        resolved_keys = set(llm_result.get("resolved_finding_keys", []))
        still_open = llm_result.get("still_open_findings", [])
        new_findings = llm_result.get("new_findings", [])
        touched_open_keys = set()

        for finding_key in resolved_keys:
            if finding_key in existing_findings:
                item = existing_findings[finding_key]
                item.status = "resolved"
                item.resolution_type = "fixed_in_source"
                item.resolved_at = datetime.now(timezone.utc)
                item.last_seen_run_id = review_run_id

        for payload in [*still_open, *new_findings]:
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
