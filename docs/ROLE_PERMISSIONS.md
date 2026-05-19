# Role Permissions

## Roles

Project access is represented by `project_members.role`.

- `owner`: creator and project administrator.
- `participant`: project collaborator.

## Phase 3 invite behavior

`POST /projects/{project_id}/invites` adds an existing user directly as a
`participant` member by `login`. It does not create pending invitations or
acceptance tokens yet.

Only `participant` can be invited or removed in this phase.

## Matrix

| Action | Owner | Participant | No member |
| --- | ---: | ---: | ---: |
| View project | Yes | Yes | No |
| Edit project | Yes | Yes | No |
| Delete project | Yes | No | No |
| List project members | Yes | Yes | No |
| Invite participants | Yes | No | No |
| Remove participants | Yes | No | No |
| Remove owner membership | No | No | No |

Owner-only permission failures use the same hidden `404 PROJECT_NOT_FOUND`
pattern as protected project deletion.
