class NullLLMClient:
    async def generate_diagnosis(
        self,
        bot_name: str,
        score: float,
        signal_breakdown: dict,
        similar_cases: list[dict],
        prompt_template: str,
        **_: dict,
    ) -> str:
        return (
            f"{bot_name} score is {score}/100 based on {signal_breakdown}. "
            f"Similar case count: {len(similar_cases)}."
        )

