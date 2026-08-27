.PHONY: help docker-start docker-down docker-restart docker-status docker-logs

COMPOSE := docker compose

help:
	@echo "Available targets:"
	@echo "  make docker-start    Start the app in the background"
	@echo "  make docker-down     Stop and remove containers without deleting data"
	@echo "  make docker-restart  Restart the running app containers"
	@echo "  make docker-status   Show container status"
	@echo "  make docker-logs     Follow app logs"

docker-start:
	$(COMPOSE) up -d

docker-down:
	$(COMPOSE) down

docker-restart:
	$(COMPOSE) restart

docker-status:
	$(COMPOSE) ps

docker-logs:
	$(COMPOSE) logs -f app
