#!/usr/bin/env bash
set -euo pipefail

# Export OpenAPI from running FastAPI app to packages/contracts/openapi.json

API_URL="${API_URL:-http://localhost:8000}"
OUT_FILE="packages/contracts/openapi.json"

echo "Fetching OpenAPI spec from ${API_URL}/openapi.json ..."
curl -sS "${API_URL}/openapi.json" -o "${OUT_FILE}"
echo "Saved OpenAPI spec to ${OUT_FILE}"

