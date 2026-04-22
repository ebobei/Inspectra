import json
import logging
import time
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

        system_prompt = (
            "You are Inspectra, a review engine for software artifacts. "
            "Return ONLY valid JSON matching the expected schema. "
            "Never repeat findings that are already resolved. "
            "If a finding remains unresolved on later iterations, keep the message shorter and calmer. "
            "Do not wrap JSON in markdown fences."
        )
        user_prompt = (
            "Analyze the current artifact and prior review context. "
            "Detect unresolved issues, resolved issues, and new issues. "
            "Return JSON with keys: summary, resolved_finding_keys, still_open_findings, new_findings, final_comment_markdown.\n\n"
            f"Payload:\n{json.dumps(prompt_payload, ensure_ascii=False)}"
        )

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
                with httpx.Client(timeout=settings.request_timeout_sec) as client:
                    response = client.post(
                        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                        headers=headers,
                        json=request_body,
                    )
                    response.raise_for_status()
                    data = response.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                self._validate_response(parsed)
                return parsed
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLM review attempt failed",
                    extra={"event_type": "llm.review.retry", "session_id": prompt_payload.get("session_id")},
                    exc_info=True,
                )
                if attempt < settings.llm_max_retries:
                    time.sleep(min(2 ** (attempt - 1), 4))

        logger.error(
            "LLM review failed, using fallback response",
            extra={"event_type": "llm.review.fallback", "session_id": prompt_payload.get("session_id")},
            exc_info=last_error,
        )
        return self._safe_fallback(prompt_payload, str(last_error) if last_error else "unknown error")

    def _validate_settings(self) -> None:
        if not settings.llm_api_key:
            raise ValueError("LLM_API_KEY is not configured")
        if not settings.llm_model:
            raise ValueError("LLM_MODEL is not configured")
        if not settings.llm_base_url:
            raise ValueError("LLM_BASE_URL is not configured")

    def _validate_response(self, parsed: dict[str, Any]) -> None:
        if not isinstance(parsed, dict):
            raise ValueError("LLM response is not a JSON object")
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

    def _safe_fallback(self, prompt_payload: dict[str, Any], reason: str) -> dict[str, Any]:
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
