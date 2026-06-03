# Role Permissions

## Roles

Project access is represented by `project_members.role`.

- `owner`: creator and project administrator.
- `participant`: project collaborator.

## Phase 3 invite behavior

`POST /projects/{project_id}/invites` creates a pending invite for an existing
user by `login`. The response includes the raw invite token once; only a
SHA-256 hash of the token is stored.

`POST /invites/accept` accepts a pending invite. The caller must be
authenticated as the invited login. Accepting the invite creates the
membership with the invited role.

Owners can invite existing users as `owner` or `participant`.
Pending invites expire after 7 days.

Owner invites are a privileged operation. They grant the same project-level
administrative permissions as the creator, including inviting members and
deleting the project. The project must always keep at least one owner; owner
removal is not exposed in this phase.

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
| Create owner invites | Yes | No | No |
| Create participant invites | Yes | No | No |
| Accept own invite | Yes | Yes | No |
| Remove participants | Yes | No | No |
| Remove owner membership | No | No | No |

Authenticated callers receive `403 PROJECT_FORBIDDEN` or
`403 DOCUMENT_FORBIDDEN` when an existing project or document is blocked by
membership or role permissions. Missing, soft-deleted, or wrong-status
resources return the relevant `404`.
