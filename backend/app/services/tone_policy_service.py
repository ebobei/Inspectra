class TonePolicyService:
    def get_tone_level(self, iteration_count: int) -> str:
        if iteration_count <= 1:
            return "strict"
        if iteration_count == 2:
            return "neutral"
        if iteration_count == 3:
            return "soft"
        return "summary_only"
