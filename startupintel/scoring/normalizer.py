def min_max(value: float, lower: float, upper: float) -> float:
    if upper == lower:
        return 0.0
    return max(0.0, min(1.0, (value - lower) / (upper - lower)))


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def weighted_score(values: dict[str, float], weights: dict[str, float]) -> float:
    return round(clamp(sum(values.get(key, 0.0) * weight for key, weight in weights.items())) * 100, 2)
