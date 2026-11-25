FROM ghcr.io/astral-sh/uv:0.13.10 AS uv
FROM python:3.12.10-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /srv/marketplace
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 PATH="/srv/marketplace/.venv/bin:$PATH"
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
RUN mkdir -p /srv/marketplace/bundled-car-photos && cp -r frontend/uploads/cars/. /srv/marketplace/bundled-car-photos/
RUN useradd --create-home marketplace && mkdir -p /tmp/celery frontend/uploads/cars && chown marketplace /tmp/celery && chown -R marketplace frontend/uploads/cars
USER marketplace
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
