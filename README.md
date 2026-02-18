# Luneta Monorepo

Luneta is a collaborative web platform to collect, review, and publish research-grade smart-glasses usage scenarios related to childhood contexts, with ethical analysis, AI-assisted suggestions, and similarity detection to reduce duplication.

## Repository structure

```text
luneta/
  README.md
  .gitignore
  .env.example
  Makefile
  pnpm-workspace.yaml

  apps/
    web/          # Vite + React SPA
    backend/      # FastAPI API + Taskiq worker + jobs

  packages/
    contracts/    # OpenAPI + generated TS types

  docs/           # Project documentation (brief, FR/NFR, ADRs, etc.)

  infra/
    docker/       # docker-compose (redis, minio, mailhog)
    scripts/      # helper scripts (openapi export, seeds, ...)

  .github/
    workflows/    # CI
```

## High-level components

- **apps/web**: Vite + React SPA (public browsing + authenticated flows).
- **apps/backend**: Single Python project (FastAPI API + Taskiq worker + jobs).
- **packages/contracts**: OpenAPI spec exported from the API and generated TypeScript types for the frontend.
- **docs**: Functional/technical docs, domain model, API contract, architecture, ADRs.
- **infra**: Local dev tooling (docker-compose, scripts).

Concrete implementation details (routes, schemas, services) can be iterated on top of this skeleton.

