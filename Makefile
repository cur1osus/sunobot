app-dir = bot

.PHONY: generate
generate:
	uv run alembic revision --m="$(NAME)" --autogenerate


.PHONY: migrate
migrate:
	uv run alembic upgrade head




.PHONY: format
format:
	uv run ruff check --fix --unsafe-fixes $(app-dir)
	uv run ruff format $(app-dir)


.PHONY: dev
dev:
	python3.12 -m compileall bot
	./run.sh .env.dev
