from app.services.diff_service import DiffService


def test_diff_service_detects_change() -> None:
    result = DiffService().compare("old", "new")
    assert result.changed is True


def test_diff_service_skips_same_text() -> None:
    result = DiffService().compare("same", "same")
    assert result.changed is False
