.PHONY: up down logs test traffic clean

up:
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f
test:
	python3 -m compileall apps
	python3 -m unittest discover -s tests
traffic:
	docker compose --profile traffic run --rm load-generator
clean:
	docker compose down -v --remove-orphans
