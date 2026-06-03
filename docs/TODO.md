# TODO

This table tracks desired route and behavior status. `matching route` and
`matching or improves behavior` use only `YES` or `NO`.

| Desired item | Current implementation | matching route | matching or improves behavior | TODO left |
| --- | --- | --- | --- | --- |
| `POST /auth/register` creates a user with login, email, password, and repeat password | `POST /auth/register` | YES | YES | None |
| `POST /auth/login` logs in with login and password | `POST /auth/login` | YES | YES | None |
| `GET /auth/me` returns the authenticated user | `GET /auth/me` | YES | YES | None |
| `GET /projects` returns accessible project fields plus document filename arrays | `GET /projects` | YES | YES | None |
| `POST /project` creates a project and makes caller owner | `POST /project` | YES | YES | None |
| `GET /project/{project_id}/info` returns project info for members | `GET /project/{project_id}/info` | YES | YES | None |
| `PATCH /project/{project_id}/info` updates project name and description | `PATCH /project/{project_id}/info` | YES | YES | None |
| `DELETE /project/{project_id}` deletes project, owner-only | `DELETE /project/{project_id}` | YES | YES | None |
| `GET /project/{project_id}/members` lists project members | `GET /project/{project_id}/members` | YES | YES | None |
| `DELETE /project/{project_id}/members/{user_id}` removes a participant | `DELETE /project/{project_id}/members/{user_id}` | YES | YES | None |
| `POST /project/{project_id}/invite?user={login}` grants participant access immediately | `POST /project/{project_id}/invite?user={login}` | YES | YES | None |
| `GET /project/{project_id}/documents` lists uploaded project documents | `GET /project/{project_id}/documents` | YES | YES | None |
| `POST /project/{project_id}/documents` uploads one document | `POST /project/{project_id}/documents` | YES | YES | None |
| `POST /project/{project_id}/documents/presign-upload` starts a presigned upload | `POST /project/{project_id}/documents/presign-upload` | YES | YES | None |
| `POST /project/{project_id}/documents/complete-upload` completes a presigned upload | `POST /project/{project_id}/documents/complete-upload` | YES | YES | None |
| `GET /document/{document_id}` downloads document bytes | `GET /document/{document_id}` | YES | YES | None |
| `GET /document/{document_id}/info` returns document metadata | `GET /document/{document_id}/info` | YES | YES | None |
| `GET /document/{document_id}/download-url` returns a presigned download URL | `GET /document/{document_id}/download-url` | YES | YES | None |
| `PUT /document/{document_id}` updates document metadata | `PUT /document/{document_id}` | YES | YES | None |
| `DELETE /document/{document_id}` deletes a document, owner-only | `DELETE /document/{document_id}` | YES | YES | None |
