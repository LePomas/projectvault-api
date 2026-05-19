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
`participant` membership.

Only `participant` can be invited or removed in this phase.
Pending invites expire after 7 days.

## Matrix

| Action | Owner | Participant | No member |
| --- | ---: | ---: | ---: |
| View project | Yes | Yes | No |
| Edit project | Yes | Yes | No |
| Delete project | Yes | No | No |
| List project members | Yes | Yes | No |
| Create participant invites | Yes | No | No |
| Accept own participant invite | Yes | Yes | No |
| Remove participants | Yes | No | No |
| Remove owner membership | No | No | No |

Owner-only permission failures use the same hidden `404 PROJECT_NOT_FOUND`
pattern as protected project deletion.
