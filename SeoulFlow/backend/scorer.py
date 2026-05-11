def compute_score(total: int, stationary: int) -> tuple[float, str]:
    if total == 0:
        return 0.0, "FREE"

    ratio = stationary / total

    if ratio <= 0.25:
        status = "FREE"
    elif ratio <= 0.50:
        status = "LIGHT"
    elif ratio <= 0.75:
        status = "HEAVY"
    else:
        status = "GRIDLOCK"

    return ratio, status
