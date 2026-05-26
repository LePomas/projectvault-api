# API Conventions

## Base URL

Local:

```text
http://localhost:8000
````

## Response format

All responses are JSON except file downloads.

## Authentication

Protected endpoints require:

```http
Authorization: Bearer <jwt_token>
```

JWT expiration:

```text
1 hour
```

## Success status codes

| Action          | Status         |
| --------------- | -------------- |
| Create resource | 201 Created    |
| Read resource   | 200 OK         |
| Update resource | 200 OK         |
| Delete resource | 204 No Content |

## Error status codes

| Error                  | Status                     |
| ---------------------- | -------------------------- |
| Invalid request body   | 422 Unprocessable Entity   |
| Invalid credentials    | 401 Unauthorized           |
| Missing token          | 401 Unauthorized           |
| No access to resource  | 403 Forbidden              |
| Resource not found     | 404 Not Found              |
| Duplicate resource     | 409 Conflict               |
| Unsupported file type  | 415 Unsupported Media Type |
| Storage limit exceeded | 413 Payload Too Large      |

## Endpoint naming

Use plural nouns:

```text
/projects
/projects/{project_id}
/projects/{project_id}/invites
/projects/{project_id}/members
/projects/{project_id}/documents
/documents/{document_id}
/documents/{document_id}/download
/invites/accept
```

Prefer `PATCH` for partial updates.

Avoid using `GET` for actions that create or modify state.

## Document uploads

Phase 4 local uploads use multipart form data:

```http
POST /projects/{project_id}/documents
Content-Type: multipart/form-data
```

Field:

```text
file
```

Supported file types:

```text
.pdf  application/pdf
.docx application/vnd.openxmlformats-officedocument.wordprocessingml.document
```

Projects have a configurable storage limit. Uploads that would exceed
`PROJECT_STORAGE_LIMIT_BYTES` return `413 PROJECT_STORAGE_LIMIT_EXCEEDED`.

`GET /documents/{document_id}` returns JSON metadata.

Rename a document:

```http
PATCH /documents/{document_id}
Content-Type: application/json
```

```json
{
  "filename": "renamed-contract.pdf"
}
```

`PUT /documents/{document_id}` remains available as a compatibility route for
the same rename payload.

Phase 4 local downloads use direct backend file responses:

```http
GET /documents/{document_id}/download
```

The download endpoint returns file bytes, not JSON, after the same project-access
checks as document metadata reads. Presigned download URLs are reserved for the
S3 phase.

## S3-compatible document uploads

Phase 5 adds S3-compatible uploads for local MinIO development and future S3
deployment. The API speaks standard S3-compatible storage through configuration;
it does not call MinIO-specific APIs.

Start an upload:

```http
POST /projects/{project_id}/documents/presign-upload
Content-Type: application/json
```

```json
{
  "filename": "contract.pdf",
  "content_type": "application/pdf",
  "size_bytes": 1234
}
```

The response creates document metadata with `status="pending_upload"` and
returns a presigned PUT URL plus required upload headers. Pending uploads do not
increment project document totals. `size_bytes` is optional; when provided, the
backend rejects the presign request before issuing an upload URL if the object
would exceed the project storage limit.

Complete an upload after the client PUTs the object:

```http
POST /projects/{project_id}/documents/complete-upload
Content-Type: application/json
```

```json
{
  "document_id": 1
}
```

The backend verifies the object in storage, reads its size, marks the document
as `uploaded`, and updates project document totals. If the verified object would
exceed the project storage limit, the backend deletes the uploaded object,
marks the pending metadata as deleted, and returns
`413 PROJECT_STORAGE_LIMIT_EXCEEDED`. Repeating completion for an already
uploaded document is idempotent.

In AWS deployments, S3 object-created events can finalize the same pending
upload through `app.lambda_handlers.s3_events.handler`. The Lambda path looks up
the pending document by `storage_key` and applies the same metadata, total-size,
idempotency, and storage-limit rules as `complete-upload`.

For local MinIO validation, `scripts/s3-event-smoke-test.sh` simulates the S3
event JSON and runs the handler inside the API container. This validates the
event finalization path locally without configuring AWS or MinIO bucket
notifications.

Get a presigned download URL:

```http
GET /documents/{document_id}/download-url
```

The response is JSON with `download_url` and `expires_in`.
