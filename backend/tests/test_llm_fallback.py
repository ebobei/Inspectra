from app.services.llm_service import LLMService


def test_safe_fallback_shape() -> None:
    service = LLMService()
    result = service._safe_fallback({"iteration_count": 2, "max_iterations": 3}, "boom")
    assert "summary" in result
    assert "final_comment_markdown" in result
    assert isinstance(result["resolved_finding_keys"], list)
