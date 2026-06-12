# Data Model (ERD)

Reflects the current ORM models in `app/models/` and the bootstrap schema in
`db/init/001_initial_schema.sql`. Verified against the repository on
2026-06-11.

> Note on invites: there is no token-based invite/accept flow and no
> `project_invites` table. Membership is granted directly through
> `POST /project/{project_id}/invite?user=<login>`, which adds the user as a
> `participant`. See [ROLE_PERMISSIONS.md](ROLE_PERMISSIONS.md).

## users

Stores registered users.

Fields:

- id
- login (unique)
- email (unique)
- password_hash (argon2 via `pwdlib`)
- created_at
- updated_at

## projects

Stores project details. Soft-deleted via `deleted_at`.

Fields:

- id
- name
- description
- owner_id (FK users.id, `ON DELETE RESTRICT`)
- total_size_bytes (CHECK >= 0, `projects_total_size_check`)
- documents_count (CHECK >= 0, `projects_documents_count_check`)
- created_at
- updated_at
- deleted_at

## project_members

Stores project access permissions. Unique on `(project_id, user_id)`.

Fields:

- id
- project_id (FK projects.id, `ON DELETE CASCADE`)
- user_id (FK users.id, `ON DELETE CASCADE`)
- role
- created_at

Roles (CHECK constraint):

- owner
- participant

## documents

Stores document metadata. Soft-deleted via `deleted_at`.

Fields:

- id
- project_id (FK projects.id, `ON DELETE CASCADE`)
- uploaded_by_id (FK users.id, `ON DELETE RESTRICT`)
- filename
- content_type
- size_bytes (CHECK >= 0, `documents_size_bytes_check`)
- storage_key (unique)
- status (`pending_upload` | `uploaded` | `rejected` | `deleted`)
- created_at
- updated_at
- deleted_at

## Relationships

- users 1:N projects as owner (`projects.owner_id`)
- users N:M projects through project_members
- projects 1:N documents
- users 1:N documents as uploader (`documents.uploaded_by_id`)

## Indexes

- projects: `owner_id`, `deleted_at`
- project_members: `project_id`, `user_id`
- documents: `project_id`, `uploaded_by_id`, `deleted_at`, `status`

> Foreign keys are declared inline in `001_initial_schema.sql` without explicit
> constraint names, so PostgreSQL auto-generates names such as
> `project_members_user_id_fkey`.
