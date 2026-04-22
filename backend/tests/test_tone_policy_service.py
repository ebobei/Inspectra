from app.services.tone_policy_service import TonePolicyService


def test_tone_policy_levels() -> None:
    service = TonePolicyService()
    assert service.get_tone_level(1) == "strict"
    assert service.get_tone_level(2) == "neutral"
    assert service.get_tone_level(3) == "soft"
    assert service.get_tone_level(4) == "summary_only"
