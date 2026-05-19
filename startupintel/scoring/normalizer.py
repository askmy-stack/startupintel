def min_max(value: float, lower: float, upper: float) -> float:
    if upper == lower:
        return 0.0
    return max(0.0, min(1.0, (value - lower) / (upper - lower)))


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def weighted_score(values: dict[str, float], weights: dict[str, float]) -> float:
    return round(clamp(sum(values.get(key, 0.0) * weight for key, weight in weights.items())) * 100, 2)


def normalize_signal(value: float, min_val: float, max_val: float, inverse: bool = False) -> float:
    """Normalize a signal value to 0-100 scale.

    Args:
        value: Input value to normalize
        min_val: Minimum expected value
        max_val: Maximum expected value
        inverse: If True, higher input values give lower scores

    Returns:
        Normalized score between 0 and 100
    """
    if max_val == min_val:
        return 50.0

    # Clamp value to range
    clamped = max(min_val, min(max_val, value))

    # Normalize to 0-1
    normalized = (clamped - min_val) / (max_val - min_val)

    if inverse:
        normalized = 1.0 - normalized

    # Scale to 0-100
    return round(normalized * 100, 2)


def normalize_score(score: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Normalize a score to 0-100 scale with clamping."""
    return normalize_signal(score, min_val, max_val, inverse=False)
