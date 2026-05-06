# Initial ERD

## users

Stores registered users.

Fields:

- id
- login
- email
- password_hash
- created_at
- updated_at

## projects

Stores project details.

Fields:

- id
- name
- description
- owner_id
- total_size_bytes
- documents_count
- created_at
- updated_at
- deleted_at

## project_members

Stores project access permissions.

Fields:

- id
- project_id
- user_id
- role
- created_at

Roles:

- owner
- participant

## documents

Stores document metadata.

Fields:

- id
- project_id
- uploaded_by_id
- filename
- content_type
- size_bytes
- storage_key
- status
- created_at
- updated_at
- deleted_at

## project_invites

Stores pending project invitations.

Fields:

- id
- project_id
- invited_login
- invited_email
- token_hash
- role
- expires_at
- accepted_at
- created_at

## Relationships

- users 1:N projects as owner
- users N:M projects through project_members
- projects 1:N documents
- users 1:N documents as uploader
- projects 1:N project_invites