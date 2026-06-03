---
title: "ProjectVault - Roadmap"
version: "1.0"
language: "es-MX"
last_updated: "2026-05-26"
purpose: "Fases, prioridades, MVP, backlog y checklist de entrega para ProjectVault."
---

# Roadmap

> Este roadmap es contexto de planeacion. No representa necesariamente el estado
> implementado del repositorio.

## Roadmap de desarrollo

Fecha de inicio sugerida: **miercoles 29 de abril de 2026**
Entrega final sugerida: **jueves 18 de junio de 2026**
Duracion: **7 semanas y 2 dias**

| Fase | Fechas | Scope | Entregable |
|---|---|---|---|
| 0 | 2026-04-29-2026-05-01 | Diseno tecnico y setup | Repo, arquitectura, DB draft, Docker local |
| 1 | 2026-05-04-2026-05-08 | Auth + usuarios | Registro, login, JWT |
| 2 | 2026-05-11-2026-05-15 | CRUD de proyectos | Crear, listar, ver, editar, borrar proyectos |
| 3 | 2026-05-18-2026-05-22 | Permisos e invitaciones | Owner/participant, invite by login |
| 4 | 2026-05-25-2026-05-29 | Documentos local/S3-ready | Upload, list, download, update, delete |
| 5 | 2026-06-01-2026-06-05 | S3 + Lambda | Presigned URLs, S3 events, size calculation |
| 6 | 2026-06-08-2026-06-12 | Tests + CI/CD | pytest, linting, Docker image, CI pipeline |
| 7 | 2026-06-15-2026-06-18 | Deployment + hardening | AWS/on-prem deploy, docs, final demo |

## Fase 0 - Setup y diseno tecnico

Fechas: **2026-04-29-2026-05-01**

### Objetivo

Dejar listo el esqueleto profesional del proyecto.

### Scope

- Crear repo.
- Definir estructura del proyecto.
- Crear `pyproject.toml`.
- Configurar FastAPI.
- Configurar Docker Compose local.
- Configurar PostgreSQL local.
- Definir ERD inicial.
- Definir arquitectura por capas.
- Definir convenciones de endpoints.
- Definir status codes esperados.

### Entregables

```text
repo/
  app/
    api/
    core/
    models/
    schemas/
    services/
    repositories/
    db/
  tests/
  docker-compose.yml
  Dockerfile
  pyproject.toml
  README.md
```

### Definition of Done

- `docker compose up` levanta API + PostgreSQL.
- `/health` responde JSON.
- README explica como correr local.
- ERD inicial documentado.

## Fase 1 - Auth y usuarios

Fechas: **2026-05-04-2026-05-08**

### Objetivo

Tener usuarios reales con login y JWT.

### Endpoints

```http
POST /auth/register
POST /auth/login
GET  /auth/me
```

### Scope

- Hash de password.
- Validacion con Pydantic.
- JWT con expiracion de 1 hora.
- Dependency para usuario autenticado.
- Manejo de errores:
  - usuario duplicado
  - password invalido
  - token expirado
  - token invalido

### Entregables

- Registro funcional.
- Login funcional.
- JWT valido por 1 hora.
- Tests de auth.

### Definition of Done

- No se guarda password plano.
- Tests cubren login correcto e incorrecto.
- Endpoints protegidos rechazan requests sin JWT.

## Fase 2 - CRUD de proyectos

Fechas: **2026-05-11-2026-05-15**

### Objetivo

Crear el core del sistema.

### Endpoints

```http
POST   /projects
GET    /projects
GET    /projects/{project_id}
PATCH  /projects/{project_id}
DELETE /projects/{project_id}
```

### Reglas

- Al crear proyecto, el usuario queda como `owner`.
- `GET /projects` solo devuelve proyectos accesibles para el usuario.
- Solo owner puede borrar.
- Owner y participant pueden editar.
- Borrado puede ser soft delete al inicio.

### Entregables

- CRUD de proyectos completo.
- Tabla `projects`.
- Tabla `project_members`.
- Tests de permisos basicos.

### Definition of Done

- Usuario A no puede ver proyectos de Usuario B.
- Owner puede borrar.
- Usuario sin acceso recibe `403` o `404`, segun decision de diseno.
- Respuestas JSON consistentes.

## Fase 3 - Roles, permisos e invitaciones

Fechas: **2026-05-18-2026-05-22**

### Objetivo

Implementar colaboracion entre usuarios.

### Endpoints

```http
POST   /projects/{project_id}/invites
GET    /projects/{project_id}/members
DELETE /projects/{project_id}/members/{user_id}
```

### Request simple para invitar usuario

```json
{
  "login": "usuario_invitado",
  "role": "participant"
}
```

Tambien se puede invitar a otro owner:

```json
{
  "login": "usuario_owner",
  "role": "owner"
}
```

### Reglas

- Solo owner puede invitar.
- Owner puede invitar usuarios como `owner` o `participant`.
- Solo owner puede quitar miembros.
- Participant puede modificar proyecto y documentos.
- Participant no puede borrar proyecto.
- Owner no puede eliminarse a si mismo si es el unico owner.
- El proyecto debe conservar al menos un owner.

### Entregables

- Sistema de roles funcional.
- Tests de autorizacion.
- Matriz de permisos documentada.

## Fase 4 - Documentos local/S3-ready

Fechas: **2026-05-25-2026-05-29**

### Objetivo

Completar la parte de documentos sin depender todavia de AWS.

### Endpoints

```http
GET    /projects/{project_id}/documents
POST   /projects/{project_id}/documents
GET    /documents/{document_id}
GET    /documents/{document_id}/download
PATCH  /documents/{document_id}
DELETE /documents/{document_id}
```

### Scope

- Solo aceptar `.pdf` y `.docx`.
- Validar `content_type`.
- Guardar metadata en PostgreSQL.
- Guardar archivo localmente o con adaptador compatible S3.
- Validar acceso por proyecto.
- Al borrar documento, borrar metadata y objeto fisico.

### Entregables

- CRUD completo de documentos.
- Tabla `documents`.
- Servicio de storage abstracto.

### Estado y pendientes

- Implementado: upload/list/read metadata/update/delete con storage local.
- Implementado: descarga directa de bytes por backend con storage local.
- Implementado: validacion `.pdf`/`.docx`, `content_type`, permisos y tests.
- Implementado: ejemplos Phase 4 en `requests.http`.
- Implementado: MinIO local como backend S3-compatible para desarrollo.
- Implementado: URLs presignadas de upload/download y `complete-upload` local.
- Implementado: limite configurable de almacenamiento por proyecto.
- Implementado: Lambda handler para procesar eventos S3 object-created.
- Implementado: smoke test local de eventos S3 simulados contra MinIO.

## Fase 5 - S3 + Lambda + limites de almacenamiento

Fechas: **2026-06-01-2026-06-05**

### Objetivo

Implementar la parte cloud del scope.

### Scope

- Usar MinIO como backend S3-compatible local para desarrollo, segun
  `docs/STORAGE_DECISION_MATRIX.md`.
- Implementar presigned upload/download.
- Guardar documentos con `storage_key` backend-agnostico.
- Configurar Lambda para eventos de S3.
- Cuando se sube archivo:
  - calcular tamano
  - actualizar `documents.size_bytes`
  - actualizar `projects.total_size_bytes`
  - opcional: generar thumbnail/preview si es imagen
- Aplicar limite de storage por proyecto.

### Endpoints sugeridos

```http
POST /projects/{project_id}/documents/presign-upload
POST /projects/{project_id}/documents/complete-upload
GET  /documents/{document_id}/download-url
```

### Entregables

- S3 funcional.
- MinIO local funcional.
- Metadata actualizada desde `complete-upload` local.
- Limite de tamano por proyecto.
- Lambda funcional.
- Smoke test local de eventos S3 simulados.

### Definition of Done

- Un archivo subido a S3 genera evento o evento simulado local.
- Lambda procesa evento real o simulado local.
- DB refleja tamano actualizado.
- Proyecto rechaza nuevos uploads si supera limite.

## Fase 6 - Testing, calidad y CI/CD

Fechas: **2026-06-08-2026-06-12**

### Objetivo

Que el proyecto se vea profesional y confiable.

### Tests requeridos

- Unit tests de servicios.
- Integration tests con PostgreSQL.
- Auth tests.
- Permission tests.
- Document tests.
- Storage mock tests.
- API tests con `TestClient` o `httpx`.

### Calidad

- Implementado: Ruff lint en CI.
- Implementado: Ruff format check en CI.
- Implementado: pytest en CI.
- Implementado: `docker compose config` en CI.
- mypy opcional.
- Coverage report.
- Implementado: Alembic baseline inicial.
- Pendiente: migraciones posteriores al baseline.
- Implementado: CI en pull request para ramas `main` y `develop`.

### Pipeline minimo

```text
on pull request:
  - install dependencies
  - lint
  - format check
  - run tests
  - validate Docker Compose config

on merge to main:
  - build API image
  - push API image to ECR
  - deploy API image to existing ECS service
  - build documents Lambda image
  - push documents Lambda image to ECR
  - update existing Lambda function image
```

### Entregables

- Implementado: GitHub Actions CI funcional.
- Implementado: tests automaticos en CI.
- Implementado en repo: GitHub Actions CD para publicar imagenes y desplegar
  recursos AWS precreados.
- Implementado live: ECR con imagenes, bucket S3 de produccion, OIDC trust,
  permisos de deploy, secrets JWT y `DATABASE_URL`, RDS PostgreSQL, ECS service,
  Lambda por imagen, notificacion S3 ObjectCreated y primer Deploy exitoso.
- Pendiente live: ingress publico/API domain, frontend productivo, IaC y
  migraciones posteriores al baseline.
- Pendiente: Badge en README.

## Fase 7 - Deployment, documentacion y demo final

Fechas: **2026-06-15-2026-06-18**

### Objetivo

Cerrar el proyecto como entrega presentable.

### Scope AWS

- Implementado en repo: workflow de deploy API a ECS existente.
- Implementado en repo: workflow de update de Lambda existente por imagen.
- Implementado live: repos ECR con imagenes, bucket S3 de produccion, OIDC
  trust, permisos de deploy, secrets `projectvault/prod/JWT_SECRET_KEY` y
  `projectvault/prod/DATABASE_URL`, RDS, ECS service, Lambda, notificacion S3 y
  variables GitHub de produccion.
- Implementado live: primer GitHub Actions Deploy exitoso.
- Pendiente live: ingress publico/API domain para exponer la API.
- Pendiente live: frontend productivo y origen CORS definitivo.
- Pendiente futuro: IaC para reemplazar configuracion manual de AWS.
- Crear usuario demo.
- Probar flujo completo.

### Scope documentacion

- README final.
- Diagrama de arquitectura.
- ERD.
- API examples.
- Decisiones tecnicas.
- Como correr local.
- Como desplegar.
- Limitaciones conocidas.
- Roadmap futuro.

### Demo final

```text
1. Register user
2. Login
3. Create project
4. Upload document
5. Invite participant
6. Login as participant
7. Update project info
8. Download document
9. Try deleting project as participant -> should fail
10. Delete project as owner -> should succeed
```

## MVP vs stretch goals

### MVP obligatorio

Debe estar listo maximo el **viernes 29 de mayo de 2026**.

```text
- Register/login
- JWT auth
- Create/list/get/update/delete projects
- Owner/participant permissions
- Invite user by login
- Upload/list/download/update/delete documents
- PostgreSQL schema
- Docker Compose local
- Basic tests
```

### Scope cloud obligatorio

Debe estar listo maximo el **viernes 5 de junio de 2026**.

```text
- S3 storage
- Presigned URLs
- Lambda triggered by S3 event
- File size calculation
- Project total storage calculation
```

### Scope profesional

Debe estar listo maximo el **viernes 12 de junio de 2026**.

```text
- CI pipeline
- Linting
- Tests
- Docker image build
- ECR image publishing workflow
- ECS deploy workflow for precreated resources
- Lambda image update workflow for precreated function
- Alembic migrations
- README usable
```

### Stretch goals

Solo hacer despues del MVP.

```text
- Email invite links
- Tokenized join links
- Image thumbnails
- Document versioning
- Audit log
- Soft delete + restore
- Project storage quota dashboard
- Admin endpoint
- PostgreSQL row-level security
- Terraform/OpenTofu
```

## Backlog por prioridad

### P0 - No negociable

```text
Auth
JWT
Users
Projects
Project members
Documents
Access control
PostgreSQL
Docker Compose
Basic tests
```

### P1 - Muy importante

```text
S3 integration
MinIO local S3-compatible backend
Lambda file-size processing
CI pipeline
Alembic migrations
Presigned URLs
Storage limits
```

### P2 - Profesionaliza el proyecto

```text
Document versioning
Invite tokens
Email invite
Audit logs
Better deployment automation
Monitoring/logging
```

### P3 - Bonus

```text
Image resize
PDF preview
Virus scanning
Full IaC
Advanced role system
Admin panel
```

## Checklist final de entrega

Antes de presentar el proyecto, verificar:

```text
[ ] docker compose up funciona
[ ] /health responde
[ ] registro de usuario funciona
[ ] login devuelve JWT
[ ] JWT expira en 1 hora
[ ] endpoints protegidos requieren JWT
[ ] usuario puede crear proyecto
[ ] creador queda como owner
[ ] usuario solo ve proyectos accesibles
[ ] owner puede borrar proyecto
[ ] participant no puede borrar proyecto
[ ] owner puede invitar participant
[ ] participant puede editar proyecto
[ ] participant puede subir documentos
[ ] participant no puede borrar documentos
[ ] documentos respetan permisos del proyecto
[ ] se aceptan solo pdf/docx en MVP
[ ] metadata de documentos se guarda en DB
[ ] MinIO local funciona como backend S3-compatible
[ ] S3/presigned URL funciona si aplica
[ ] Lambda actualiza size metadata si aplica
[ ] tests pasan localmente
[ ] CI corre lint + format check + tests + Compose config
[ ] README explica setup local
[ ] README explica estado actual de deployment
[ ] README explica deployment productivo
[ ] ERD incluido
[ ] demo script incluido
```

## Entrega final recomendada

El repo deberia incluir:

```text
README.md
PROJECT_PLAN.md
ARCHITECTURE.md
API.md
DEPLOYMENT.md
docker-compose.yml
Dockerfile
pyproject.toml
alembic/
app/
tests/
docs/
```

Este archivo puede vivir como:

```text
docs/projectvault_llm_instructions.md
```

O como:

```text
PROJECT_PLAN.md
```
