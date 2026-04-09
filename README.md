# Luneta Monorepo

Luneta is a collaborative web platform to collect, review, and publish research-grade smart-glasses usage scenarios related to childhood contexts, with ethical analysis, AI-assisted suggestions, and similarity detection to reduce duplication.

## Levantar todo en local (un comando)

```bash
cp .env.example .env   # solo la primera vez (en PowerShell: copy .env.example .env)
make up
```

En **Windows sin Make**, usa Docker Compose directo:

```powershell
copy .env.example .env
docker compose up -d --build
```

Para parar: `docker compose down`. Ver [docs/FUNDACIONES-TECNICAS.md](docs/FUNDACIONES-TECNICAS.md) para más comandos y desarrollo con hot-reload.

## Repository structure

```text
luneta/
  README.md
  .env.example
  Makefile
  docker-compose.yml   # stack completo (mongo, redis, api, worker, web, ...)
  pnpm-workspace.yaml

  apps/
    api/               # Backend principal: FastAPI + Taskiq
    web/               # Vite + React SPA

  packages/
    contracts/         # OpenAPI + generated TS types

  infra/
    docker/            # compose/scripts adicionales
    mongo-init/        # opcional: scripts init MongoDB
    scripts/           # openapi export, seeds, ...

  docs/                # Documentación (FUNDACIONES-TECNICAS, ADRs, etc.)
  .github/workflows/   # CI
```

## High-level components

- **apps/api**: Backend principal FastAPI + Taskiq (app/main.py, routes/, tasks/, worker.py).
- **apps/web**: Vite + React SPA (public browsing + authenticated flows).
- **packages/contracts**: OpenAPI spec + TypeScript types for the frontend.
- **infra**: Local dev (docker-compose en raíz + scripts en infra/).
- **docs**: [Fundaciones técnicas](docs/FUNDACIONES-TECNICAS.md), ADRs, etc.

