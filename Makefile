.PHONY: up down api-test api-lint migrate
up:
	docker compose up --build

down:
	docker compose down

api-test:
	docker compose run --rm api pytest -q

api-lint:
	docker compose run --rm api ruff check app tests

migrate:
	docker compose run --rm api alembic upgrade head
