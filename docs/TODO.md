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
| Frontend automated tests | CI runs Vitest, typecheck, and build for the frontend | Keep browser e2e opt-in/local for now | None |
| Browser e2e smoke | Opt-in local Playwright smoke covers auth, project, member, and document flows with mocked API responses | Keep browser e2e local-only until frontend deployment is ready | Wire into CI later only if runtime cost is acceptable |
| Public frontend hosting | Static S3 and CloudFront hosting selected for `https://app.lepomas.xyz` | Precreated S3 bucket, CloudFront distribution, ACM certificate, and DNS-only Cloudflare record | Create or wire the AWS/Cloudflare resources before the first frontend deploy |
| Frontend CI/CD deploy | Deploy workflow is ready to build, upload, and invalidate the frontend | Automated frontend deploy to S3 and CloudFront | Set frontend GitHub production variables, then run one cutover deploy |
| Backend CORS for public frontend | API allows `http://localhost:3000` | API also allows `https://app.lepomas.xyz` | Update `CORS_ALLOWED_ORIGINS` production variable and redeploy the backend |
| Controlled demo readiness | API demo ingress exists with ALB allowlist | Approved reviewer can reach both frontend and API | Verify reviewer IP allowlist, live API health, frontend load, and browser CORS before review |
