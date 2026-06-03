# TODO

This checklist tracks the desired functionality and API shape. The current code
uses the canonical plural routes documented in `docs/API_CONVENTIONS.md`; route
aliases listed here are backlog items unless already present.

## Desired functionality

- [x] User login/auth
- [x] Create/Delete projects
- [x] Add/Update project's info/details - name, description
- [x] Add/Update/Remove projects documents (docx, pdf)
- [x] Share project with other users to access

## Desired API

- [ ] `POST /auth` - Create user (login, password, repeat password)
  - Current equivalent: `POST /auth/register` with `login`, `email`, and
    `password`.
- [ ] `POST /login` - Login into service (login, password)
  - Current equivalent: `POST /auth/login`.
- [x] `POST /projects` - Create project from details (name, description).
  Automatically gives access to created project to user, making him the owner
  (admin of the project).
- [ ] `GET /projects` - Get all projects, accessible for a user. Returns list
  of projects full info(details + documents).
  - Current response contains project details and document totals; full document
    metadata is available through `GET /projects/{project_id}/documents`.
- [ ] `GET /project/<project_id>/info` - Return project's details, if user has
  access.
  - Current equivalent: `GET /projects/{project_id}`.
- [ ] `PUT /project/<project_id>/info` - Update projects details - name,
  description. Returns the updated project's info.
  - Current equivalent: `PATCH /projects/{project_id}`.
- [ ] `DELETE /project/<project_id>` - Delete project, can only be performed by
  the projects' owner. Deletes the corresponding documents.
  - Current equivalent: `DELETE /projects/{project_id}`. Project delete is
    owner-only and currently soft-deletes the project.
- [x] `GET /project/<project_id>/documents` - Return all of the project's
  documents.
  - Current route: `GET /projects/{project_id}/documents`.
- [x] `POST /project/<project_id>/documents` - Upload document/documents for a
  specific project.
  - Current route: `POST /projects/{project_id}/documents` for one multipart
    file, plus S3-compatible presigned upload endpoints.
- [x] `GET /document/<document_id>` - Download document, if the user has access
  to the corresponding project.
  - Current metadata route: `GET /documents/{document_id}`.
  - Current local download route: `GET /documents/{document_id}/download`.
  - Current presigned download route: `GET /documents/{document_id}/download-url`.
- [x] `PUT /document/<document_id>` - Update document.
  - Current route: `PUT /documents/{document_id}` remains as rename
    compatibility; preferred route is `PATCH /documents/{document_id}`.
- [x] `DELETE /document/<document_id>` - Delete document and remove it from the
  corresponding project.
  - Current route: `DELETE /documents/{document_id}`. Document delete is
    owner-only.
- [ ] `POST /project/<project_id>/invite?user=<login>` - Grant access to the
  project for a specific user. If the request is not coming from the owner of
  the project, results in error. Granting access gives participant permissions
  to receiving user.
  - Current flow: `POST /projects/{project_id}/invites` creates an invite token,
    then `POST /invites/accept` accepts it.
