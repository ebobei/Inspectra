from typing import Any


class PromptBuilder:
    def build_review_payload(
        self,
        *,
        source_type: str,
        previous_text: str | None,
        current_text: str,
        open_findings: list[dict[str, Any]],
        tone_level: str,
        iteration_count: int,
        max_iterations: int,
    ) -> dict[str, Any]:
        return {
            "source_type": source_type,
            "previous_text": previous_text,
            "current_text": current_text,
            "open_findings": open_findings,
            "tone_level": tone_level,
            "iteration_count": iteration_count,
            "max_iterations": max_iterations,
            "instructions": {
                "do_not_repeat_resolved_findings": True,
                "repeat_unresolved_findings_more_softly": iteration_count > 1,
            },
        }
