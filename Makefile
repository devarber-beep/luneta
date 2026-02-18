# Makefile for common Luneta dev tasks

.PHONY: web backend worker test openapi seed-orgs

web:
\tcd apps/web && pnpm install && pnpm dev

backend:
\tcd apps/backend && uvicorn luneta.api.main:app --reload

worker:
\tcd apps/backend && python -m luneta.worker.broker

test:
\tcd apps/backend && pytest

openapi:
\tbash infra/scripts/export_openapi.sh

seed-orgs:
\tpython infra/scripts/seed_orgs.py

