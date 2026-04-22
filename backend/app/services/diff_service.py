from dataclasses import dataclass


@dataclass
class DiffResult:
    changed: bool
    old_text: str
    new_text: str


class DiffService:
    def compare(self, old_text: str | None, new_text: str) -> DiffResult:
        old = old_text or ""
        return DiffResult(changed=old != new_text, old_text=old, new_text=new_text)
