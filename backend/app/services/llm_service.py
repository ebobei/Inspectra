import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    REQUIRED_KEYS = {
        "summary",
        "resolved_finding_keys",
        "still_open_findings",
        "new_findings",
        "final_comment_markdown",
    }

    def review(self, prompt_payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_settings()

        payload_json = json.dumps(prompt_payload, ensure_ascii=False, indent=2)
        system_prompt = self._load_prompt_file("review_system", default=self._default_system_prompt())
        user_prompt_template = self._load_prompt_file("review_user", default=self._default_user_prompt())
        user_prompt = user_prompt_template.replace("{payload_json}", payload_json)

        request_body = {
            "model": settings.llm_model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None

        for attempt in range(1, settings.llm_max_retries + 1):
            try:
                with httpx.Client(
                    timeout=settings.request_timeout_sec,
                    verify=settings.llm_verify_ssl,
                ) as client:
                    response = client.post(
                        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                        headers=headers,
                        json=request_body,
                    )
                    response.raise_for_status()
                    data = response.json()

                content = data["choices"][0]["message"]["content"]
                parsed = self._parse_json_content(content)
                return self._normalize_response(parsed, prompt_payload)

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLM review attempt failed",
                    extra={
                        "event_type": "llm.review.retry",
                        "session_id": prompt_payload.get("session_id"),
                        "attempt": attempt,
                        "llm_verify_ssl": settings.llm_verify_ssl,
                    },
                    exc_info=True,
                )

                if attempt < settings.llm_max_retries:
                    time.sleep(min(2 ** (attempt - 1), 4))

        logger.error(
            "LLM review failed, using fallback response",
            extra={
                "event_type": "llm.review.fallback",
                "session_id": prompt_payload.get("session_id"),
                "llm_verify_ssl": settings.llm_verify_ssl,
            },
            exc_info=(
                (type(last_error), last_error, last_error.__traceback__)
                if last_error
                else None
            ),
        )
        return self._safe_fallback(
            prompt_payload,
            str(last_error) if last_error else "unknown error",
        )

    def _validate_settings(self) -> None:
        if not settings.llm_api_key:
            raise ValueError("LLM_API_KEY is not configured")
        if not settings.llm_model:
            raise ValueError("LLM_MODEL is not configured")
        if not settings.llm_base_url:
            raise ValueError("LLM_BASE_URL is not configured")

    def _load_prompt_file(self, name: str, *, default: str) -> str:
        language = (settings.review_prompt_language or "ru").strip().lower()
        prompt_dir = Path(__file__).resolve().parents[1] / "prompts"
        prompt_path = prompt_dir / f"{name}.{language}.txt"

        try:
            text = prompt_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            logger.warning(
                "Prompt file not found; using built-in fallback prompt",
                extra={
                    "event_type": "llm.prompt.fallback",
                    "prompt_path": str(prompt_path),
                    "prompt_language": language,
                },
            )
            return default

        return text or default

    def _parse_json_content(self, content: Any) -> dict[str, Any]:
        if not isinstance(content, str):
            raise ValueError("LLM response content is not a string")

        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text).strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise
            parsed = json.loads(text[start : end + 1])

        if not isinstance(parsed, dict):
            raise ValueError("LLM response is not a JSON object")
        return parsed

    def _normalize_response(
        self,
        parsed: dict[str, Any],
        prompt_payload: dict[str, Any],
    ) -> dict[str, Any]:
        missing = self.REQUIRED_KEYS.difference(parsed.keys())
        if missing:
            raise ValueError(f"LLM response missing keys: {sorted(missing)}")

        if not isinstance(parsed["resolved_finding_keys"], list):
            raise ValueError("resolved_finding_keys must be a list")

        if not isinstance(parsed["still_open_findings"], list):
            raise ValueError("still_open_findings must be a list")

        if not isinstance(parsed["new_findings"], list):
            raise ValueError("new_findings must be a list")

        if not isinstance(parsed["final_comment_markdown"], str):
            raise ValueError("final_comment_markdown must be a string")

        tone_level = str(prompt_payload.get("tone_level") or "neutral")
        return {
            "summary": str(parsed.get("summary") or ""),
            "resolved_finding_keys": [
                str(item).strip()
                for item in parsed.get("resolved_finding_keys", [])
                if str(item).strip()
            ],
            "still_open_findings": self._normalize_findings(
                parsed.get("still_open_findings", []),
                default_tone_level=tone_level,
            ),
            "new_findings": self._normalize_findings(
                parsed.get("new_findings", []),
                default_tone_level=tone_level,
            ),
            "final_comment_markdown": parsed["final_comment_markdown"].strip(),
        }

    def _normalize_findings(
        self,
        findings: list[Any],
        *,
        default_tone_level: str,
    ) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []

        for raw in findings:
            if not isinstance(raw, dict):
                logger.warning(
                    "Skipping malformed LLM finding because it is not an object",
                    extra={"event_type": "llm.finding.skipped"},
                )
                continue

            category = self._clean_text(raw.get("category"), default="general")
            severity = self._clean_text(raw.get("severity"), default="medium")
            title = self._clean_text(raw.get("title"), default="Review finding")
            description = self._clean_text(raw.get("description"), default=title)
            tone_level = self._clean_text(raw.get("tone_level"), default=default_tone_level)
            finding_key = self._clean_text(raw.get("finding_key") or raw.get("key"), default="")

            if not finding_key:
                finding_key = self._build_finding_key(
                    category=category,
                    severity=severity,
                    title=title,
                    description=description,
                )
                logger.warning(
                    "LLM finding did not contain finding_key; generated a fallback key",
                    extra={
                        "event_type": "llm.finding_key.generated",
                        "finding_key": finding_key,
                    },
                )

            normalized.append(
                {
                    "finding_key": finding_key,
                    "category": category,
                    "severity": severity,
                    "title": title,
                    "description": description,
                    "tone_level": tone_level,
                }
            )

        return normalized

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

    def _default_system_prompt(self) -> str:
        return (
            "Ты Inspectra, движок review для инженерных артефактов. "
            "Верни только валидный JSON по ожидаемой схеме. "
            "Не оборачивай JSON в markdown. "
            "У каждого замечания обязательно должен быть finding_key."
        )

    def _default_user_prompt(self) -> str:
        return (
            "Проанализируй текущий артефакт и предыдущий контекст review. "
            "Верни JSON с ключами: summary, resolved_finding_keys, "
            "still_open_findings, new_findings, final_comment_markdown.\n\n"
            "Payload:\n{payload_json}"
        )

    def _safe_fallback(
        self,
        prompt_payload: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        iteration_count = prompt_payload.get("iteration_count")
        max_iterations = prompt_payload.get("max_iterations")

        return {
            "summary": "LLM response validation failed; returning safe fallback.",
            "resolved_finding_keys": [],
            "still_open_findings": [],
            "new_findings": [],
            "final_comment_markdown": (
                "## Inspectra Review\n\n"
                "The review engine could not produce a reliable structured response from the configured LLM. "
                "No new findings were published from this run.\n\n"
                f"- Iteration: {iteration_count}/{max_iterations}\n"
                f"- Reason: {reason}\n"
            ),
        }
