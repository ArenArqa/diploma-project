Aren's diplom work

# AutoMetric — Smart Car Marketplace & Rental Platform

A fourth-year Python diploma project for Armenia: sale and rental listings, explainable valuation, dynamic daily pricing, and PostgreSQL-enforced booking safety. Prices are in **AMD**, distances in kilometers, and business dates use **Asia/Yerevan**.

## Start the demo

Prerequisites: Docker Engine with Compose v2, Python 3.12+, and Make. Python is only needed on the host to generate local configuration; application dependencies run in Docker.

```sh
make bootstrap
```

This generates `.env` if absent, builds the image, starts PostgreSQL/Redis, applies migrations, seeds synthetic data, and starts API, Celery worker, and Celery Beat. Existing configuration and data are preserved. Run migrations again when updating an existing checkout; `make up` alone does not migrate.

- Application: <http://localhost:8000>
- Interactive REST documentation: <http://localhost:8000/docs>
- Readiness: <http://localhost:8000/api/v1/health/ready>

Demo accounts:

| Account | Capabilities |
|---|---|
| `user@demo.example.com` | Sell owned cars, value cars, reserve rentals |
| `dealer@demo.example.com` | Sell/rent owned inventory, view market and inventory insights |
| `admin@demo.example.com` | Manage all inventory and user/dealer roles, view platform insights |

Their password is the generated `DEMO_PASSWORD` in your local `.env`. Tokens last 30 minutes and stay in browser memory; refreshing the page signs you out.

```sh
docker compose ps
docker compose logs -f api celery_worker
docker compose exec api python -m scripts.evaluate_valuation
docker compose exec api python -m scripts.create_admin your-email@example.com --name Administrator
make down
```

`make down` (or `docker compose down`) stops all five services and retains database and uploaded-image volumes. Compose uses the fixed project name `diploma-project`, so these commands keep targeting the same containers and data after the checkout directory is renamed. Seeding is explicit and additive: it never resets existing accounts or prices. It creates 6 brands, 12 models, 240 sale listings, 48 rental listings, example price histories, and past/upcoming bookings. Baselines and listings are **synthetic**.

## Windows: one-command launch

Install and start Docker Desktop with **Linux containers** enabled and Docker Compose v2.20 or newer. Then open PowerShell in the project folder and run:

```powershell
.\start.cmd
```

Python, Make, and a local virtual environment are not required. The launcher creates `.env` with random secrets if missing, builds the containers, waits for PostgreSQL/Redis, applies migrations, seeds the local photos and demo data, starts all five services, and opens <http://localhost:8000> after the API health check passes. Existing `.env`, accounts, listings, and custom uploads are preserved. The first run needs internet access to download container images and Python dependencies; bundled car photos need no downloads. Repeat the same command on later runs.

Stop everything while retaining the database and uploaded images:

```powershell
.\stop.cmd
```

From Command Prompt, use `start.cmd` and `stop.cmd`. Both commands locate the project using their own file path, so they also work when invoked from another directory or a path containing spaces. Use `.\start.cmd -NoBrowser` to skip opening a browser. Scripts return a nonzero exit code if Docker, a migration, or another startup step fails; inspect `docker compose logs --tail 80` for container details. If startup fails after some services have started, `.\stop.cmd` stops them. Keep Docker Desktop running until shutdown completes.

Docker Desktop and a separate WSL Docker Engine have separate data stores. A fresh Windows Docker installation seeds its own demo; moving existing accounts or uploaded files between engines requires transferring their Docker volumes.

## Business rules

### Car images and publishing

Use **List a car** in the marketplace to create a sale listing (users) or sale/rental listing (dealers). Select an optional local image to preview it before publishing. The form saves the car, uploads its image, then publishes the listing; if an upload fails, retry continues with the saved car.

`POST /api/v1/cars/{car_id}/image` accepts a multipart `file` from the owner or admin. JPG/JPEG, PNG, and WebP are supported, up to 5 MiB and 20 megapixels. The server validates extension, MIME type, and decoded contents, generates a UUID filename, and returns the updated car including `image_url`. Clients cannot set arbitrary image URLs through JSON requests.

Images are served locally from `/uploads/cars/<brand_slug>/<model_slug>_<n>.jpg`. The repository includes **36 distinct real Wikimedia Commons photographs: three for every one of the twelve models**, with front/rear views and different colors/generations. Every JPEG exceeds 15 KiB, is at least 1200 pixels wide, and is decoded and checksum-validated before deployment. Photographs match the exact brand/model; model years and individual listing condition are illustrative.

Source filenames, photographer credits, and CC BY-SA 4.0 license links are recorded in `data/car_image_sources.json` and the public `/uploads/cars/credits.json`. The [photo credit gallery](http://localhost:8000/static/image-credits.html) displays all local images and their attribution. Resized derivatives retain the original license. Viewing the marketplace and gallery uses local image files and does not contact Wikimedia.

The explicit maintenance fetch command downloads the curated sources from Wikimedia's public image CDN. This avoids reliance on the metadata API, which can be rate-limited, and avoids automatic search results that may contain different models or interiors:

```sh
uv run python -m scripts.fetch_car_images
```

The command validates existing downloads and resumes missing ones, honors retry responses, and refuses incomplete or duplicate datasets. Source manifest changes automatically replace the affected cached images; `--refresh` forces all downloads again. Normal `make bootstrap` and seeding require **no image downloads**.

Docker's `car_images` volume preserves images across rebuilds. Bundled brand/model directories and credits are copied into an existing volume during seeding or the explicit update command. Model photo assignments rotate in listing order, producing varied adjacent cards even when filtering to one model:

```sh
docker compose build api
docker compose run --rm api python -m scripts.update_car_images
docker compose up -d api
```

Re-seeding also runs the same assignment logic. Generic demo renders and missing URLs are replaced with model-specific photos. Custom images uploaded through the owner/dealer endpoint retain their UUID URLs and are never overwritten by this process. Images can be uploaded as JPG/JPEG, PNG, or WebP. Existing user-uploaded files are retained for cached links, and the vector illustration remains a fallback for missing/broken images.

- Users publish sale listings. Dealers and admins may publish rental listings for eligible owned cars. Admins may manage existing cars belonging to others.
- One physical car, identified by its unique VIN, can have only one active listing.
- Rental dates are inclusive: January 1–3 is three days. Another reservation can start January 4, not January 3.
- Rentals last 1–90 days and end within 365 days of today.
- A quote freezes its price for ten minutes and does not hold inventory. Accepting it rechecks availability inside a transaction.
- Reusing a quote returns the same reservation. A cancelled quote cannot create another reservation; request a new quote.
- Renter, owning dealer, or admin can cancel before the start date. Existing reservations block archive/specification changes until they finish.
- Progressive duration discounts: days 1–6 at full rate, 7–29 at 90%, and 30 onward at 80%. Seasonal and demand factors apply per day.
- The valuation interval is a **heuristic range**, calibrated from synthetic asking prices. It is not a real-world accuracy claim or an observed sale-price forecast.

## Local development

Install [uv](https://docs.astral.sh/uv/), then:

```sh
uv sync --frozen
make init
docker compose up -d db redis
```

For local processes, use host database names instead of Docker service names. Load the generated secrets and override the connection URLs in your shell:

```sh
set -a
. ./.env
set +a
export DATABASE_URL=postgresql+asyncpg://marketplace:marketplace@localhost:5432/marketplace
export REDIS_URL=redis://localhost:6379/0
export CELERY_BROKER_URL=redis://localhost:6379/1
uv run alembic upgrade head
uv run python -m scripts.seed_demo
uv run uvicorn app.main:app --reload
```

Separate terminals can run:

```sh
uv run celery -A app.tasks.celery_app:celery_app worker --loglevel=INFO --concurrency=2
uv run celery -A app.tasks.celery_app:celery_app beat --loglevel=INFO --schedule=/tmp/autometric-beat
```

Run only one Beat scheduler per environment. Market snapshots update every five minutes; seeding computes the first batch immediately.

## Tests

```sh
uv run pytest tests/unit -q
uv run ruff check .
uv run ruff format --check .
```

Integration tests use a separate PostgreSQL database, Redis database 15 for cache, and Redis database 14 for the test Celery broker. They truncate **only the explicitly configured test database**, never the demo database.

Create the test database once:

```sh
docker compose exec db createdb -U marketplace marketplace_test
```

Then run:

```sh
TEST_DATABASE_URL=postgresql+asyncpg://marketplace:marketplace@localhost:5432/marketplace_test \
TEST_REDIS_URL=redis://localhost:6379/15 \
CELERY_BROKER_URL=redis://localhost:6379/14 \
uv run pytest -q
```

Without these test URLs, infrastructure tests are explicitly skipped. The suite checks real PostgreSQL exclusion constraints, twenty concurrent reservation attempts, idempotent quote acceptance, cancellations, cache behavior, ownership, and a real Celery worker process. Do not run multiple test suites against the same test database concurrently.

## Design and defense materials

- [Architecture, schema, indexes, and API contracts](docs/architecture.md)
- [Valuation and rental pricing methodology](docs/valuation_methodology.md)
- [Thesis defense walkthrough](docs/defense_demo.md)

FastAPI serves the minimal Vanilla JS interface. Tailwind CDN and Google Fonts are optional visual enhancements; local CSS preserves the interface when those networks are unavailable. The application uses no external market data or payment service.
