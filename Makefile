.PHONY: help docker-start docker-down docker-restart docker-reload docker-status docker-logs

COMPOSE := docker compose

help:
	@echo "Available targets:"
	@echo "  make docker-start    Start the app in the background"
	@echo "  make docker-down     Stop and remove containers without deleting data"
	@echo "  make docker-restart  Rebuild and restart the app without deleting data"
	@echo "  make docker-reload   Restart running containers without rebuilding"
	@echo "  make docker-status   Show container status"
	@echo "  make docker-logs     Follow app logs"

docker-start:
	$(COMPOSE) up -d

docker-down:
	$(COMPOSE) down

docker-restart:
	$(COMPOSE) up -d --build

docker-reload:
	$(COMPOSE) restart

docker-status:
	$(COMPOSE) ps

docker-logs:
	$(COMPOSE) logs -f app
