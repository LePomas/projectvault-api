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

`GET /documents/{document_id}` returns JSON metadata. File-byte downloads are a
separate concern from metadata reads.
