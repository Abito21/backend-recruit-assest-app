format:
	uv run ruff format .
	uv run ruff check . --fix

dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	uv run celery -A app.tasks.celery_tasks worker --pool=solo -c 1 --loglevel=info