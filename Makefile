.PHONY: init bootstrap up down clean-docker clean-builder delete-volumes test check
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
# These prune commands affect the current Docker engine across all projects.
# Docker asks for confirmation; neither command deletes volumes.
clean-docker:
	@echo "Remove unused Docker resources across ALL projects; volumes are preserved."
	docker system prune --all
clean-builder:
	@echo "Remove unused default-builder cache across ALL projects; volumes are preserved."
	docker builder prune --all
# Explicit opt-in is required because Compose does not prompt for volume deletion.
delete-volumes:
	@if [ "$(CONFIRM)" != "DELETE" ]; then \
		echo "This stops the project and permanently deletes its database, Redis data, and uploaded images."; \
		echo "To proceed, run: make delete-volumes CONFIRM=DELETE"; \
		exit 1; \
	fi
	docker compose down --volumes
test:
	uv run pytest
check:
	uv run ruff check .
