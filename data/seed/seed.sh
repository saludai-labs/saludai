#!/bin/sh
# Seed HAPI FHIR with Argentine synthetic data.
# Expects FHIR_SERVER_URL env var (e.g. http://hapi-fhir:8080/fhir).
# Polls until HAPI is ready (distroless image has no shell for Docker healthcheck).

set -e

BUNDLE_PATH="/seed/seed_bundle.json"
MAX_RETRIES=60
RETRY_INTERVAL=5

echo "==> Waiting for FHIR server at ${FHIR_SERVER_URL} ..."

for i in $(seq 1 "$MAX_RETRIES"); do
  if curl -sf "${FHIR_SERVER_URL}/metadata" > /dev/null 2>&1; then
    echo "==> FHIR server is ready (attempt ${i})"
    break
  fi
  if [ "$i" -eq "$MAX_RETRIES" ]; then
    echo "==> ERROR: FHIR server not ready after $((MAX_RETRIES * RETRY_INTERVAL))s"
    exit 1
  fi
  echo "  Waiting... (attempt ${i}/${MAX_RETRIES})"
  sleep "$RETRY_INTERVAL"
done

echo "==> Seeding FHIR server..."

# POST the transaction bundle
HTTP_CODE=$(curl -s -o /tmp/response.json -w "%{http_code}" \
  -X POST "${FHIR_SERVER_URL}" \
  -H "Content-Type: application/fhir+json" \
  -d @"${BUNDLE_PATH}")

if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
  echo "==> Bundle posted successfully (HTTP ${HTTP_CODE})"
else
  echo "==> ERROR: Bundle POST failed (HTTP ${HTTP_CODE})"
  cat /tmp/response.json
  exit 1
fi

# Verify patient count
PATIENT_COUNT=$(curl -s "${FHIR_SERVER_URL}/Patient?_summary=count" \
  | grep -o '"total" *: *[0-9]*' \
  | grep -o '[0-9]*')

echo "==> Patient count: ${PATIENT_COUNT}"

if [ "${PATIENT_COUNT}" -ge 50 ]; then
  echo "==> Seed verification PASSED (${PATIENT_COUNT} >= 50 patients)"
else
  echo "==> ERROR: Seed verification FAILED (${PATIENT_COUNT} < 50 patients)"
  exit 1
fi

# Verify condition count
CONDITION_COUNT=$(curl -s "${FHIR_SERVER_URL}/Condition?_summary=count" \
  | grep -o '"total" *: *[0-9]*' \
  | grep -o '[0-9]*')

echo "==> Condition count: ${CONDITION_COUNT}"
echo "==> Seeding complete!"
