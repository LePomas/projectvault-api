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

## Frontend deployment TODO

| Area | Current state | Target | TODO left |
| --- | --- | --- | --- |
| Frontend live smoke testing | Browser-verified controlled demo flow against `https://api.lepomas.xyz` | Live smoke covers register/login, JWT restore, `/auth/me`, project create/list/detail, member grant/list, and document upload/list/download | None |
| Frontend automated tests | CI runs `npm run typecheck` and `npm run build` | First focused frontend test layer | Add tests for API client error handling and critical auth/project flows |
| Browser e2e smoke | No browser e2e runner is configured | Opt-in smoke path for the controlled demo UI | Add Playwright or equivalent for auth, project, member, and document review flows |
| Public frontend hosting | App runs locally on `http://localhost:3000` | AWS static hosting at `https://app.lepomas.xyz` | Create or wire precreated S3 and CloudFront resources for the Vite build output |
| Frontend containerization | No frontend Dockerfile exists | Static hosting preferred | Add containerization only if the frontend is later hosted as an ECS/container service |
| Frontend CI/CD deploy | CI builds frontend; deploy workflow is backend/Lambda only | Automated frontend deploy | Add build, S3 upload, CloudFront invalidation, and required GitHub production variables |
| Backend CORS for public frontend | API allows `http://localhost:3000` | API also allows `https://app.lepomas.xyz` | Update `CORS_ALLOWED_ORIGINS` and redeploy the backend |
| Controlled demo readiness | API demo ingress exists with ALB allowlist | Approved reviewer can reach both frontend and API | Verify reviewer IP allowlist, live API health, frontend load, and browser CORS before review |
