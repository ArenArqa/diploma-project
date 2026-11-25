import numpy as np

from app.pricing_engine.types import factor, money


def calibrate(ratios: list[float], observation_ages: list[float]):
    if not ratios:
        return factor(1), factor(0)
    logs = np.log(np.asarray(ratios, dtype=float))
    mad = float(np.median(np.abs(logs - np.median(logs))))
    if len(ratios) < 5:
        return factor(1), factor(mad)
    weights = np.exp2(-np.asarray(observation_ages) / 30)
    shrinkage = len(ratios) / (len(ratios) + 20)
    multiplier = np.clip(np.exp(shrinkage * np.average(logs, weights=weights)), 0.85, 1.15)
    return factor(float(multiplier)), factor(mad)


def quartiles(prices):
    if not prices:
        return None, None, None
    from decimal import Decimal

    values = np.quantile([float(p) for p in prices], [0.25, 0.5, 0.75])
    return tuple(money(Decimal(str(v))) for v in values)
