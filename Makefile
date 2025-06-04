# ENV
ENV_FILE = .env

# Docker
up:
	docker compose-up --build

down:
	docker compose-down

restart: down up

# Тесты
test:
	pytest --tb=short --disable-warnings -c pytest.ini

test-cov:
	pytest --cov=app --cov-report=term --cov-report=html

# Alembic
migrate:
	alembic revision --autogenerate -m "auto"

upgrade:
	alembic upgrade head

# Docs
docs:
	python -m app.utils.generate_docs

# Очистка
clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete

# Запуск локально
run:
	uvicorn app.main:app --reload
