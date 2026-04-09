# Fundaciones Técnicas

Objetivo: que el proyecto se sostenga y no se caiga al crecer. **Un comando** levanta todo en local y el skeleton está listo para extender.

## Cómo levantar todo

```bash
# Opción 1: Un comando (recomendado)
make up
# o con rebuild: make up-build

# Opción 2: Sin Make
docker compose up -d
```

Esto levanta:

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| mongo    | 27017  | MongoDB |
| redis    | 6379   | Redis (Taskiq) |
| minio    | 9000, 9001 | S3-compatible (objetos) |
| mailhog  | 1025, 8025 | SMTP dev + UI |
| api      | 8000   | FastAPI (apps/api) |
| worker   | -      | Taskiq worker |
| web      | 5173   | Vite/React |

- **Parar:** `make down` o `docker compose down`
- **Logs:** `make logs` o `docker compose logs -f`

## Make vs docker-compose

- **docker-compose**: orquesta los servicios (infra + api + worker + web). Es la fuente de verdad para “qué se levanta”.
- **Makefile**: atajos y documentación para el día a día (`make up`, `make down`, `make dev`, `make api`, etc.).

Recomendación: **usar ambos**. El “un comando” es `make up` (que llama a `docker compose up -d`). Para desarrollo con hot-reload, levanta solo la infra con `make up` y en otras terminales `make api`, `make worker`, `make web`.

## Estructura del repo (objetivo)

```text
luneta/
  apps/
    api/                    # FastAPI + Taskiq (skeleton actual)
      app/
        main.py
        settings.py
        db.py
        routes/
          health.py
        tasks/
          example.py
      worker.py
      pyproject.toml
      Dockerfile
    web/                    # Vite + React
      Dockerfile
      ...
  infra/
    docker/                 # compose legacy o scripts
    mongo-init/             # opcional: scripts init MongoDB
    scripts/
  packages/
    contracts/              # OpenAPI + tipos TS
  .env.example
  docker-compose.yml        # en raíz: todo el stack
  Makefile
  README.md
```

`apps/api` es el backend activo y único del proyecto.

## Requisitos

- Docker y Docker Compose
- Para desarrollo local sin Docker de api/web: Python ≥3.11, Node 20+, pnpm

## Variables de entorno

Copia `.env.example` a `.env` y ajusta. Con `make up` / `docker compose up`, los servicios usan los valores del compose (mongo, redis, minio, mailhog por nombre de servicio). Para correr api/worker en local, usa `localhost` en las URIs.
