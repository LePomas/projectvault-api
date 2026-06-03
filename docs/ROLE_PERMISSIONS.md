# Role Permissions

## Roles

Project access is represented by `project_members.role`.

- `owner`: creator and project administrator.
- `participant`: project collaborator.

## Invite behavior

`POST /project/{project_id}/invite?user={login}` immediately grants
`participant` membership to an existing user. The caller must be a project
owner. The route does not support owner grants.

The `project_invites` table remains in the schema for now, but public token
acceptance is not exposed by the API.

## Matrix

| Action | Owner | Participant | No member |
| --- | ---: | ---: | ---: |
| View project | Yes | Yes | No |
| Edit project | Yes | Yes | No |
| Delete project | Yes | No | No |
| View documents | Yes | Yes | No |
| Upload documents | Yes | Yes | No |
| Update documents | Yes | Yes | No |
| Delete documents | Yes | No | No |
| List project members | Yes | Yes | No |
| Grant owner access | No | No | No |
| Grant participant access | Yes | No | No |
| Remove participants | Yes | No | No |
| Remove owner membership | No | No | No |

Authenticated callers receive `403 PROJECT_FORBIDDEN` or
`403 DOCUMENT_FORBIDDEN` when an existing project or document is blocked by
membership or role permissions. Missing, soft-deleted, or wrong-status
resources return the relevant `404`.
