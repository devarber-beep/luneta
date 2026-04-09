# Luneta - atajos de desarrollo
#
# Estrategia: docker-compose orquesta todos los servicios; Make da un solo comando.
#
#   make up      → Levanta todo (mongo, redis, minio, mailhog, api, worker, web)
#   make down    → Para y elimina contenedores
#   make dev     → Solo infra en Docker; api, worker y web en local (hot-reload)
#
# Opcional: make api, make worker, make web para correr una app en local.

# En Windows, Make debe usar cmd.exe para ejecutar los comandos (evita CreateProcess failed)
ifeq ($(OS),Windows_NT)
	SHELL := cmd.exe
	.SHELLFLAGS := /c
endif

.PHONY: up down dev api worker web test openapi seed-orgs

# --- Un comando: levantar todo
up:
	docker compose up -d

up-build:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

# --- Desarrollo local (infra en Docker, apps en tu máquina)
dev: up
	@echo "Infra levantada. En otras terminales: make api, make worker, make web"

# --- Apps en local (requieren make up o servicios ya levantados)
api:
	cd apps/api && pip install -e . && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	cd apps/api && pip install -e . && taskiq worker worker:broker

web:
	cd apps/web && pnpm install && pnpm dev

# --- Tests y utilidades
test:
	cd apps/api && pip install -e ".[dev]" && pytest

openapi:
	bash infra/scripts/export_openapi.sh

seed-orgs:
	python infra/scripts/seed_orgs.py
