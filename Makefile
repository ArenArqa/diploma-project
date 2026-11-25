.PHONY: init bootstrap up down test check
init:
	python3 scripts/init_env.py
bootstrap: init
	docker compose up -d db redis
	docker compose build
	docker compose run --rm api alembic upgrade head
	docker compose run --rm api python -m scripts.seed_demo
	docker compose up -d
up:
	docker compose up -d --build
down:
	docker compose down
test:
	uv run pytest
check:
	uv run ruff check .
