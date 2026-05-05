from app.services.llm_service import LLMService


def test_safe_fallback_shape() -> None:
    service = LLMService()
    result = service._safe_fallback({"iteration_count": 2, "max_iterations": 3}, "boom")
    assert "summary" in result
    assert "final_comment_markdown" in result
    assert isinstance(result["resolved_finding_keys"], list)


def test_llm_response_normalizes_missing_finding_key() -> None:
    service = LLMService()
    result = service._normalize_response(
        {
            "summary": "found issues",
            "resolved_finding_keys": [],
            "still_open_findings": [],
            "new_findings": [
                {
                    "category": "requirements",
                    "severity": "medium",
                    "title": "No acceptance criteria",
                    "description": "The issue does not describe how to verify the result.",
                    "tone_level": "strict",
                }
            ],
            "final_comment_markdown": "## Review",
        },
        {"tone_level": "strict"},
    )

    finding = result["new_findings"][0]
    assert finding["finding_key"].startswith("requirements:")
    assert finding["title"] == "No acceptance criteria"
