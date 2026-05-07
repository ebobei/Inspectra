import httpx
import pytest

from app.services.llm_service import LLMReviewError, LLMService
import app.services.llm_service as llm_module


class FakeHTTPErrorResponse:
    status_code = 504
    reason_phrase = "Gateway Time-out"

    def raise_for_status(self):
        request = httpx.Request("POST", "https://llm.example.test/chat/completions")
        response = httpx.Response(504, request=request, text="<html>nginx timeout</html>")
        raise httpx.HTTPStatusError("504", request=request, response=response)

    def json(self):
        return {}


class FakeHTTPErrorClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def post(self, *args, **kwargs):
        return FakeHTTPErrorResponse()


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


def test_llm_response_rejects_html_error_page() -> None:
    service = LLMService()

    with pytest.raises(LLMReviewError, match="HTML error page"):
        service._parse_json_content(
            "<html><head><title>504 Gateway Time-out</title></head><body>nginx</body></html>"
        )


def test_llm_review_raises_instead_of_returning_fallback_on_http_error(monkeypatch) -> None:
    monkeypatch.setattr(llm_module.settings, "llm_api_key", "test-key")
    monkeypatch.setattr(llm_module.settings, "llm_model", "test-model")
    monkeypatch.setattr(llm_module.settings, "llm_base_url", "https://llm.example.test")
    monkeypatch.setattr(llm_module.settings, "llm_max_retries", 1)
    monkeypatch.setattr(llm_module.httpx, "Client", FakeHTTPErrorClient)

    with pytest.raises(LLMReviewError, match="HTTP 504"):
        LLMService().review({"session_id": "session-1"})
