from uuid import UUID, uuid5, NAMESPACE_DNS

from startupintel.bots.base import BaseBot, BotResult
from startupintel.events.topics import STARTUP_ACQUI_SIGNAL
from startupintel.scoring.normalizer import clamp


GROUP_WEIGHTS = {"team": 0.30, "tech": 0.25, "network": 0.25, "financial": 0.20}
DEFAULT_ACQUIRERS = [
    {"name": "Google", "domain": "google.com", "tech_overlap": 0.92, "team_fit": 0.88, "network_overlap": 0.80},
    {"name": "Microsoft", "domain": "microsoft.com", "tech_overlap": 0.85, "team_fit": 0.82, "network_overlap": 0.76},
    {"name": "Apple", "domain": "apple.com", "tech_overlap": 0.78, "team_fit": 0.84, "network_overlap": 0.62},
    {"name": "Meta", "domain": "meta.com", "tech_overlap": 0.80, "team_fit": 0.77, "network_overlap": 0.70},
    {"name": "Salesforce", "domain": "salesforce.com", "tech_overlap": 0.74, "team_fit": 0.73, "network_overlap": 0.68},
]


class AcquiBot(BaseBot):
    name = "acqui"
    required_signals = [
        "faang_alumni_ratio",
        "top10_uni_ratio",
        "founder_prior_exit",
        "avg_years_experience",
        "tech_stack_rarity_score",
        "personal_repo_stars",
        "investor_acquirer_overlap",
        "linkedin_connections_at_acquirers",
        "runway_stress_score",
        "months_since_last_raise",
    ]

    async def fetch_signals(self, startup_id: UUID) -> dict:
        raise NotImplementedError("AcquiBot fetch_signals requires team, GitHub, and funding connectors.")

    async def compute_score(self, raw: dict) -> dict[str, float]:
        return self.group_scores(raw)

    def get_weights(self) -> dict[str, float]:
        return GROUP_WEIGHTS

    def build_rag_query(self, raw: dict) -> str:
        return f"acqui-hire team quality tech rarity acquirer overlap {raw}"

    def diagnosis_prompt_template(self) -> str:
        return "Explain acqui-hire probability, top features, and likely acquirers."

    def group_scores(self, raw: dict) -> dict[str, float]:
        team = (
            clamp(float(raw.get("faang_alumni_ratio", 0.0)))
            + clamp(float(raw.get("top10_uni_ratio", 0.0)))
            + (1.0 if raw.get("founder_prior_exit") else 0.0)
            + clamp(float(raw.get("avg_years_experience", 0.0)) / 15.0)
        ) / 4.0
        tech = (
            clamp(float(raw.get("tech_stack_rarity_score", 0.0)))
            + clamp(float(raw.get("personal_repo_stars", 0.0)) / 5000.0)
        ) / 2.0
        network = (
            clamp(float(raw.get("investor_acquirer_overlap", 0.0)))
            + clamp(float(raw.get("linkedin_connections_at_acquirers", 0.0)) / 100.0)
        ) / 2.0
        financial = (
            clamp(float(raw.get("runway_stress_score", 0.0)) / 100.0)
            + clamp(float(raw.get("months_since_last_raise", 0.0)) / 24.0)
        ) / 2.0
        return {"team": team, "tech": tech, "network": network, "financial": financial}

    def feature_importances(self, raw: dict) -> dict[str, float]:
        raw_scores = {key: abs(float(value)) for key, value in raw.items() if isinstance(value, int | float)}
        total = sum(raw_scores.values()) or 1.0
        return {key: round(value / total, 4) for key, value in raw_scores.items()}

    def likely_acquirers(self, acquirers: list[dict] | None = None) -> list[dict]:
        ranked = []
        for acquirer in acquirers or DEFAULT_ACQUIRERS:
            fit_score = (
                0.4 * acquirer["tech_overlap"]
                + 0.35 * acquirer["team_fit"]
                + 0.25 * acquirer["network_overlap"]
            )
            ranked.append(
                {
                    "acquirer_id": uuid5(NAMESPACE_DNS, acquirer["domain"]),
                    "name": acquirer["name"],
                    "domain": acquirer["domain"],
                    "fit_score": round(fit_score, 3),
                    "tech_overlap": acquirer["tech_overlap"],
                    "team_fit": acquirer["team_fit"],
                    "network_overlap": acquirer["network_overlap"],
                    "rationale": f"{acquirer['name']} ranks well on tech, team, and network fit.",
                }
            )
        return sorted(ranked, key=lambda item: item["fit_score"], reverse=True)[:5]

    async def maybe_emit_event(self, result: BotResult) -> None:
        probability = result.score / 100.0
        if probability <= 0.60 or self.producer is None:
            return
        await self.producer.emit(STARTUP_ACQUI_SIGNAL, {"startup_id": str(result.startup_id), "probability": probability})

