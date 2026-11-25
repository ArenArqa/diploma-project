"""Held-out synthetic evaluation; this does not measure real-world market accuracy."""

import csv
import json
import random
from decimal import Decimal
from pathlib import Path

import numpy as np

from app.core import clock
from app.models.enums import Condition
from app.pricing_engine.valuation import estimate_sale


def evaluate():
    rng = random.Random(2026)
    targets, predictions, covered = [], [], []
    with (Path(__file__).resolve().parents[1] / "data/demo_baselines.csv").open() as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        for _ in range(50):
            result = estimate_sale(
                baseline=Decimal(row["base_price_amd"]),
                year=clock.today().year - rng.randint(0, 20),
                mileage_km=rng.randint(0, 350000),
                condition=rng.choice(list(Condition)),
                current_year=clock.today().year,
            )
            target = float(result["recommended_price"]) * rng.lognormvariate(0, 0.16)
            targets.append(target)
            predictions.append(float(result["recommended_price"]))
            covered.append(float(result["min_price"]) <= target <= float(result["max_price"]))
    actual, predicted = np.array(targets), np.array(predictions)
    return {
        "dataset": "held-out synthetic targets; no real-world accuracy claim",
        "samples": len(targets),
        "mae_amd": round(float(np.mean(np.abs(actual - predicted))), 2),
        "median_absolute_percentage_error": round(
            float(np.median(np.abs(actual - predicted) / actual) * 100), 2
        ),
        "heuristic_range_coverage_percent": round(float(np.mean(covered) * 100), 2),
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
