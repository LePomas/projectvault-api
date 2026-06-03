#!/usr/bin/env bash
set -euo pipefail

# Smoke-test the S3 presigned upload flow through the local API.
#
# Usage:
#   ./scripts/s3-smoke-test.sh
#   BASE=http://localhost:8000 ./scripts/s3-smoke-test.sh

BASE="${BASE:-http://localhost:8000}"
LOGIN="s3smoke$(date +%s)"
EMAIL="$LOGIN@example.com"
PASSWORD="super-secret-123"
SMOKE_FILE="/tmp/projectvault-smoke.pdf"
RESPONSE_FILE="/tmp/projectvault-smoke-response.json"

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
require_command jq

echo "Registering smoke-test user: $LOGIN"
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
    -d '{"name":"S3 Smoke Test","description":"Testing AWS S3 presigned upload"}'
)"
PROJECT_ID="$(require_json_field "$project_response" ".id")"
print_json_or_raw "$project_response"

echo "Requesting presigned upload URL..."
PRESIGN="$(
  api_request POST "/project/$PROJECT_ID/documents/presign-upload" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"filename":"smoke.pdf","content_type":"application/pdf"}'
)"
print_json_or_raw "$PRESIGN"

UPLOAD_URL="$(require_json_field "$PRESIGN" ".upload_url")"
DOCUMENT_ID="$(require_json_field "$PRESIGN" ".document_id")"

printf '%s\n' '%PDF-1.7 smoke test' > "$SMOKE_FILE"

echo "Uploading smoke PDF through presigned URL..."
upload_status="$(
  curl -sS -o /tmp/projectvault-smoke-upload-response.txt -w "%{http_code}" \
    -X PUT "$UPLOAD_URL" \
    -H "Content-Type: application/pdf" \
    --data-binary @"$SMOKE_FILE"
)"
if [[ "$upload_status" != "200" ]]; then
  echo "Expected upload HTTP 200, got $upload_status" >&2
  cat /tmp/projectvault-smoke-upload-response.txt >&2
  exit 1
fi
echo "Upload returned HTTP 200."

echo "Completing upload in API..."
complete_response="$(
  api_request POST "/project/$PROJECT_ID/documents/complete-upload" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"document_id\":$DOCUMENT_ID}"
)"
print_json_or_raw "$complete_response"

status="$(require_json_field "$complete_response" ".status")"
if [[ "$status" != "uploaded" ]]; then
  echo "Expected document status uploaded, got: $status" >&2
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
if [[ "$downloaded_content" != "%PDF-1.7 smoke test" ]]; then
  echo "Unexpected downloaded content:" >&2
  printf '%s\n' "$downloaded_content" >&2
  exit 1
fi

echo "S3 smoke test passed."
