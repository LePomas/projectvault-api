#!/usr/bin/env bash
set -euo pipefail

# Smoke-test the S3 event-driven upload flow through local MinIO and the Lambda
# handler. Unlike s3-smoke-test.sh, this does not call complete-upload.
#
# Usage:
#   ./scripts/s3-event-smoke-test.sh
#   BASE=http://localhost:8000 ./scripts/s3-event-smoke-test.sh

BASE="${BASE:-http://localhost:8000}"
S3_BUCKET="${S3_BUCKET:-projectvault-documents}"
LOGIN="s3eventsmoke$(date +%s)"
EMAIL="$LOGIN@example.com"
PASSWORD="super-secret-123"
SMOKE_FILE="/tmp/projectvault-event-smoke.pdf"
RESPONSE_FILE="/tmp/projectvault-event-smoke-response.json"
UPLOAD_RESPONSE_FILE="/tmp/projectvault-event-smoke-upload-response.txt"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_json_field() {
  local json="$1"
  local field="$2"
  local value

  value="$(jq -r "$field // empty" <<<"$json")"
  if [[ -z "$value" || "$value" == "null" ]]; then
    echo "Expected JSON field not found: $field" >&2
    echo "$json" | jq . >&2
    exit 1
  fi

  printf '%s' "$value"
}

print_json_or_raw() {
  local body="$1"

  if jq -e . >/dev/null 2>&1 <<<"$body"; then
    echo "$body" | jq .
  else
    printf '%s\n' "$body"
  fi
}

api_request() {
  local method="$1"
  local path="$2"
  shift 2

  local status
  : > "$RESPONSE_FILE"
  if ! status="$(
    curl -sS -o "$RESPONSE_FILE" -w "%{http_code}" \
      -X "$method" "$BASE$path" \
      "$@"
  )"; then
    echo "API request failed: $method $path could not connect to $BASE" >&2
    exit 1
  fi

  if [[ "$status" -lt 200 || "$status" -ge 300 ]]; then
    echo "API request failed: $method $path returned HTTP $status" >&2
    if [[ -s "$RESPONSE_FILE" ]]; then
      print_json_or_raw "$(cat "$RESPONSE_FILE")" >&2
    fi
    exit 1
  fi

  cat "$RESPONSE_FILE"
}

require_command curl
require_command docker
require_command jq

echo "Registering event smoke-test user: $LOGIN"
register_response="$(
  api_request POST "/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"login\":\"$LOGIN\",\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"repeat_password\":\"$PASSWORD\"}"
)"
print_json_or_raw "$register_response"

echo "Logging in..."
login_response="$(
  api_request POST "/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"login\":\"$LOGIN\",\"password\":\"$PASSWORD\"}"
)"
TOKEN="$(require_json_field "$login_response" ".access_token")"

echo "Creating project..."
project_response="$(
  api_request POST "/project" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"S3 Event Smoke Test","description":"Testing S3 event finalization"}'
)"
PROJECT_ID="$(require_json_field "$project_response" ".id")"
print_json_or_raw "$project_response"

printf '%s\n' '%PDF-1.7 event smoke test' > "$SMOKE_FILE"
SMOKE_SIZE="$(wc -c <"$SMOKE_FILE" | tr -d ' ')"

echo "Requesting presigned upload URL..."
PRESIGN="$(
  api_request POST "/project/$PROJECT_ID/documents/presign-upload" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"filename\":\"event-smoke.pdf\",\"content_type\":\"application/pdf\",\"size_bytes\":$SMOKE_SIZE}"
)"
print_json_or_raw "$PRESIGN"

UPLOAD_URL="$(require_json_field "$PRESIGN" ".upload_url")"
DOCUMENT_ID="$(require_json_field "$PRESIGN" ".document_id")"
STORAGE_KEY="$(require_json_field "$PRESIGN" ".storage_key")"

echo "Uploading smoke PDF through presigned URL..."
upload_status="$(
  curl -sS -o "$UPLOAD_RESPONSE_FILE" -w "%{http_code}" \
    -X PUT "$UPLOAD_URL" \
    -H "Content-Type: application/pdf" \
    --data-binary @"$SMOKE_FILE"
)"
if [[ "$upload_status" != "200" ]]; then
  echo "Expected upload HTTP 200, got $upload_status" >&2
  cat "$UPLOAD_RESPONSE_FILE" >&2
  exit 1
fi
echo "Upload returned HTTP 200."

echo "Processing simulated S3 object-created event..."
event_json="$(
  jq -nc --arg bucket "$S3_BUCKET" --arg key "$STORAGE_KEY" \
    '{Records:[{eventName:"ObjectCreated:Put",s3:{bucket:{name:$bucket},object:{key:$key}}}]}'
)"
handler_response="$(
  docker compose exec -T api python -c '
import json
import sys
from app.lambda_handlers.s3_events import handler

print(json.dumps(handler(json.loads(sys.argv[1]), None)))
' "$event_json"
)"
print_json_or_raw "$handler_response"

processed="$(require_json_field "$handler_response" ".processed")"
if [[ "$processed" != "1" ]]; then
  echo "Expected handler processed count 1, got: $processed" >&2
  exit 1
fi

echo "Reading document metadata after event..."
document_response="$(
  api_request GET "/document/$DOCUMENT_ID/info" \
    -H "Authorization: Bearer $TOKEN"
)"
print_json_or_raw "$document_response"

status="$(require_json_field "$document_response" ".status")"
size_bytes="$(require_json_field "$document_response" ".size_bytes")"
if [[ "$status" != "uploaded" ]]; then
  echo "Expected document status uploaded, got: $status" >&2
  exit 1
fi
if [[ "$size_bytes" != "$SMOKE_SIZE" ]]; then
  echo "Expected document size $SMOKE_SIZE, got: $size_bytes" >&2
  exit 1
fi

echo "Requesting presigned download URL..."
DOWNLOAD="$(
  api_request GET "/document/$DOCUMENT_ID/download-url" \
    -H "Authorization: Bearer $TOKEN"
)"
print_json_or_raw "$DOWNLOAD"

DOWNLOAD_URL="$(require_json_field "$DOWNLOAD" ".download_url")"

echo "Downloading smoke PDF through presigned URL..."
downloaded_content="$(curl -sSL "$DOWNLOAD_URL")"
if [[ "$downloaded_content" != "%PDF-1.7 event smoke test" ]]; then
  echo "Unexpected downloaded content:" >&2
  printf '%s\n' "$downloaded_content" >&2
  exit 1
fi

echo "S3 event smoke test passed."
