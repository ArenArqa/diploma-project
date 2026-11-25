# Thesis defense walkthrough

## Preparation

1. Run `make bootstrap` and open http://localhost:8000.
2. Obtain the generated demo password from local `.env` (`DEMO_PASSWORD`).
3. Keep http://localhost:8000/docs open in another tab.
4. Check `docker compose ps`; API, PostgreSQL, Redis, worker, and Beat should be running.

## Demonstration

1. **Catalog:** filter Toyota cars by year, mileage, fuel, and price. Change ordering and pages. Explain that public prices represent asking amounts for sale or base daily rates for rent.
2. **Price history:** open a listing and show the two seeded historical prices. An owner/admin can change a price with `PATCH /api/v1/listings/{id}` through Swagger; search invalidates its cached generation and history gains a record.
3. **Valuation:** open Car valuation, choose a model, and calculate. Change mileage or condition, then explain baseline, depreciation, excess-mileage penalty, condition, market adjustment, and heuristic range. State that the data is synthetic.
4. **Rental calendar:** sign in as `user@demo.example.com`. Choose a rental, inspect blocked dates, and choose a free period. Both boundary dates count as occupied days.
5. **Dynamic price:** request a seven-day quote. Inspect the day-seven duration factor and any season boundary. Quotes last ten minutes and do not hold dates.
6. **Confirm:** reserve the quoted car. The calendar becomes blocked and the reservation appears below. The accepted amount is frozen.
7. **Conflict:** through Swagger, submit a quote request for the occupied interval; it returns `409 booking_overlap`. For proof against simultaneous attempts and writers bypassing the API, run the booking concurrency/constraint tests shown below.
8. **Cancel and rebook:** cancel a future reservation. The dates become available. Request a new quote before rebooking; accepting an already used quote returns its existing reservation.
9. **Insights:** sign out and log in as `dealer@demo.example.com`. Show inventory counts and model-level snapshots with observation times and sample counts. Admin inventory counts cover the whole platform.
10. **Architecture:** show the ER diagram and PostgreSQL exclusion constraint in `architecture.md`.

## Focused technical checks

Use the test database setup from the README, then:

```sh
uv run pytest tests/integration/test_booking_concurrency.py tests/integration/test_booking_constraints.py -q
uv run pytest tests/integration/test_market_statistics.py -q
uv run python -m scripts.evaluate_valuation
```

Keep `TEST_DATABASE_URL`, `TEST_REDIS_URL`, and `CELERY_BROKER_URL` configured as documented. Without test URLs, infrastructure tests skip explicitly.

Twenty competing quotes for the same car and dates yield one successful reservation and nineteen conflicts. Repeated concurrent acceptance of one quote yields one reservation identifier. A direct database insert violating availability fails with PostgreSQL SQLSTATE `23P01`.

## Operational details

- Tokens last 30 minutes; sign in again if one expires.
- Seeded unavailable dates are relative to the initial seed date. Re-running the seed preserves existing bookings rather than moving them.
- Initial market snapshots are computed during seeding; Beat refreshes them every five minutes.
- A database outage makes readiness fail. Redis failure allows database-backed API operation and neutral pricing fallbacks when statistics age out.
- No payment is collected and no sale checkout is implemented. Booking value in analytics is reservation value.
