# Explainable valuation and dynamic pricing

All coefficients and baseline prices are illustrative, versioned diploma parameters. Current versions are `sale-v1`, `rent-v1`, and baseline dataset `demo-v1`. NumPy calculates robust statistics; Decimal handles monetary multiplication and half-up whole-AMD rounding. API decimals use fixed-point strings.

## Sale valuation

Let `B` be the model’s synthetic new-equivalent AMD baseline, `a=max(0,current_business_year-year)`, and `m` the mileage.

- `D(0)=1`; otherwise `D(a)=max(.12, .85*.90**(a-1))`.
- `excess=max(0,m-15000*a)`; `M=max(.65,exp(-.035*excess/10000))`.
- Condition `C`: poor `.80`, fair `.90`, good `1`, excellent `1.08`.
- Unadjusted recommendation: `B*D*M*C`.

The age curve already represents typical usage; penalizing only excess mileage avoids charging twice for ordinary mileage. Mileage below the expectation does not receive a premium.

For same-model active sale comparables observed during the last 90 inclusive business dates:

1. Normalize each asking price: `r_i=P_i/(B*D_i*M_i*C_i)`.
2. Weight by recency: `w_i=2**(-observation_age_days/30)`.
3. Shrink toward baseline: `alpha=n/(n+20)`.
4. Market adjustment: `K=clip(exp(alpha*weighted_mean(log(r_i))),.85,1.15)`.

With fewer than five usable observations, stale/missing snapshots, or mismatched baseline versions, use `K=1`. Snapshots older than ten minutes are stale. The final recommendation is `B*D*M*C*K`.

For at least five usable observations, range width is:

`u=clip(1.4826*MAD(log(r_i)) + .20/sqrt(n+1), .10, .35)`.

Otherwise use `.35`. Bounds are `recommendation*(1-u)` and `recommendation*(1+u)`, calculated from the unrounded recommendation and rounded to positive whole AMD. The API returns every factor and sample provenance.

This is a **heuristic range**, not a calibrated 95% confidence or prediction interval. Comparables are asking prices rather than completed transactions, and repeated observations of the same listing are not counted as separate comparables.

## Rental pricing

Rental dates are inclusive: `N=(end-start).days+1`. Each occupied day has:

`daily_price=round_AMD(base_daily_rate * season_factor * demand_factor * duration_factor)`.

Sum rounded daily prices to obtain the contract total. The average daily rate is display-only, rounded to two decimal places; it is not multiplied back to recover the total.

Duration discounts are progressive:

| Day number | Multiplier |
|---|---:|
| 1–6 | 1.00 |
| 7–29 | 0.90 |
| 30–90 | 0.80 |

Every extra day adds a positive price. The discount does not retrospectively reprice earlier days.

Season factors apply to each date, including cross-month rentals:

| Months | Multiplier |
|---|---:|
| January–February | 0.90 |
| March–May | 1.00 |
| June–August | 1.20 |
| September–November | 1.00 |
| December | 1.10 |

For the model’s current active rental fleet, compute `occupancy=occupied_car_days/(30*active_car_count)` over today through today+29. Only confirmed reservations intersecting that window contribute; cancelled reservations do not. Each physical car contributes at most 30 occupied days because booking overlap is forbidden.

`demand_factor=clip(.85+.50*occupancy,.85,1.35)`.

Missing or stale occupancy uses `1`, rather than interpreting missing evidence as zero demand. Demand represents near-term model-level activity and is deliberately independent of the requested rental dates in v1.

## Price and data provenance

Quotes persist their complete breakdown and source snapshot identifier. Quotes are immutable through the API and valid for ten minutes. They do not reserve dates. Acceptance honors their frozen amount, even after a listing rate or market snapshot changes, and atomically checks live availability. Booking responses read that accepted quote rather than recalculating prices.

Market statistics use a repeatable database snapshot and commit one atomic batch. Public search cache staleness is bounded by its 60-second TTL. Availability and booking checks never use the cache.

## Evaluation

Run `python -m scripts.evaluate_valuation` to generate 600 held-out synthetic observations with an independent fixed random seed and lognormal target noise. It reports MAE in AMD, median absolute percentage error, and heuristic-range coverage.

The evaluation measures behavior against known synthetic rules. It does not validate the coefficients or baseline assumptions for Armenia. Real predictive evaluation would require licensed, representative transaction data, temporal holdouts, stronger condition/trim features, and empirical interval calibration.
