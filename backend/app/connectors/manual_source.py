class ManualSourceAdapter:
    def normalize(self, *, title: str, text: str) -> dict:
        normalized_text = f"# {title}\n\n{text}".strip()
        return {
            "raw_payload": {"title": title, "text": text},
            "normalized_text": normalized_text,
            "metadata": {},
        }
