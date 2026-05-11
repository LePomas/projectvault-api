---
title: "ProjectVault - LLM-Friendly Project Instructions"
version: "1.0"
language: "es-MX"
last_updated: "2026-05-11"
purpose: "Guía accionable para implementar un backend de gestión de proyectos, perfiles y documentos con FastAPI, PostgreSQL, S3, Lambda y CI/CD."
---

# ProjectVault - Instrucciones LLM-Friendly para el Repo

## 1. Objetivo del proyecto

Construir un servicio backend llamado **ProjectVault**: una API segura para crear, actualizar, compartir y eliminar información de proyectos, incluyendo detalles del proyecto y documentos adjuntos.

El sistema debe permitir que usuarios registrados creen proyectos, suban documentos, inviten a otros usuarios y controlen permisos por proyecto.

La solución debe ser viable como proyecto académico/profesional y demostrar conocimientos de:

- Python moderno
- FastAPI
- PostgreSQL
- Autenticación con JWT
- Diseño de APIs REST
- Control de permisos
- Manejo de archivos
- S3-compatible storage
- AWS Lambda / procesamiento por eventos
- Docker
- Testing
- CI/CD
- Deployment cloud o self-hosted

---

## 2. Stack recomendado

### Stack base

| Área | Tecnología recomendada |
|---|---|
| Lenguaje | Python 3.12+ |
| API | FastAPI |
| Validación | Pydantic v2 |
| Base de datos | PostgreSQL |
| ORM | SQLAlchemy 2.x |
| Migraciones | Alembic |
| Driver PostgreSQL | psycopg 3 |
| Auth | JWT, expiración de 1 hora |
| Storage cloud | AWS S3 |
| Procesamiento de eventos | AWS Lambda triggered by S3 event |
| Desarrollo local | Docker Compose |
| Testing | pytest |
| Calidad | Ruff, optional mypy |
| Packaging | uv or Poetry |
| CI/CD | GitHub Actions or GitLab CI |

### Alternativas aceptables

| Área | Alternativa |
|---|---|
| ORM | SQLModel, si se prioriza velocidad sobre control fino |
| Storage local | Local filesystem adapter |
| Storage self-hosted | MinIO |
| Background jobs on-premise | Celery, RQ, Arq |
| Deployment AWS | ECS Fargate, App Runner, Elastic Beanstalk |
| Deployment self-hosted | Docker Compose + VPS + reverse proxy |
| Reverse proxy | Caddy, Nginx, Traefik |

---

## 3. Descripción funcional

### Funcionalidad obligatoria

El sistema debe permitir:

1. Registrar usuarios.
2. Iniciar sesión.
3. Emitir JWT válido por 1 hora.
4. Crear proyectos.
5. Listar proyectos accesibles por usuario.
6. Ver detalles de un proyecto.
7. Actualizar nombre y descripción de un proyecto.
8. Eliminar proyectos, solo si el usuario es owner.
9. Subir documentos a un proyecto.
10. Listar documentos de un proyecto.
11. Descargar documentos si el usuario tiene acceso.
12. Actualizar documentos.
13. Eliminar documentos.
14. Invitar usuarios a un proyecto.
15. Manejar permisos owner/participant.
16. Validar todos los datos con Pydantic.
17. Responder siempre JSON, excepto cuando se devuelva contenido binario de archivo.
18. Usar status codes HTTP correctos.

### Funcionalidad opcional

1. Enviar invitación por email.
2. Generar link de invitación con token hasheado.
3. Aceptar invitación desde browser.
4. Redimensionar imágenes con Lambda.
5. Calcular tamaño total de archivos por proyecto.
6. Aplicar límite de almacenamiento por proyecto.
7. Versionado de documentos.
8. Audit log.
9. Soft delete.
10. PostgreSQL Row-Level Security.
11. Terraform/OpenTofu.

---

## 4. API recomendada

Usar nombres REST consistentes en plural.

### Auth

```http
POST /auth/register
POST /auth/login
GET  /auth/me
```

### Projects

```http
POST   /projects
GET    /projects
GET    /projects/{project_id}
PATCH  /projects/{project_id}
DELETE /projects/{project_id}
```

### Project members and invites

```http
POST   /projects/{project_id}/invites
GET    /projects/{project_id}/members
DELETE /projects/{project_id}/members/{user_id}
```

### Documents

```http
GET    /projects/{project_id}/documents
POST   /projects/{project_id}/documents
GET    /documents/{document_id}
PUT    /documents/{document_id}
DELETE /documents/{document_id}
```

### S3 presigned flow, recomendado para producción

```http
POST /projects/{project_id}/documents/presign-upload
POST /projects/{project_id}/documents/complete-upload
GET  /documents/{document_id}/download-url
```

---

## 5. Reglas de negocio

### Usuarios

- Cada usuario tiene login único.
- Las contraseñas nunca se guardan en texto plano.
- El login devuelve un JWT.
- El JWT debe expirar en 1 hora.
- Todos los endpoints de negocio deben requerir JWT.

### Proyectos

- Al crear un proyecto, el usuario creador se convierte automáticamente en `owner`.
- Un proyecto puede tener múltiples usuarios asociados.
- Un proyecto debe tener al menos un owner.
- Solo usuarios con acceso pueden ver el proyecto.
- Owner y participant pueden actualizar detalles del proyecto.
- Solo owner puede eliminar el proyecto.

### Documentos

- Cada documento pertenece a un proyecto.
- Solo usuarios con acceso al proyecto pueden ver/descargar documentos.
- Owner y participant pueden agregar, actualizar y eliminar documentos.
- Al borrar un proyecto, deben borrarse o marcarse como eliminados sus documentos correspondientes.
- Solo se aceptan archivos `.pdf` y `.docx` para el MVP.
- Guardar metadata del archivo en PostgreSQL.
- El archivo físico debe guardarse localmente, en S3 o en un storage compatible.

### Invitaciones

- Solo owner puede invitar usuarios.
- La invitación por login asigna rol `participant`.
- Participant no puede invitar a otros usuarios.
- Participant no puede eliminar el proyecto.

---

## 6. Matriz de permisos

| Acción | Owner | Participant | No member |
|---|---:|---:|---:|
| Ver proyecto | Sí | Sí | No |
| Editar proyecto | Sí | Sí | No |
| Eliminar proyecto | Sí | No | No |
| Ver documentos | Sí | Sí | No |
| Subir documentos | Sí | Sí | No |
| Actualizar documentos | Sí | Sí | No |
| Eliminar documentos | Sí | Sí | No |
| Invitar usuarios | Sí | No | No |
| Quitar usuarios | Sí | No | No |

---

## 7. Modelo de base de datos recomendado

### Tablas mínimas

```text
users
projects
project_members
documents
```

### Tablas recomendadas para versión profesional

```text
users
projects
project_members
documents
document_versions
project_invites
storage_events
audit_logs
```

### users

Campos sugeridos:

```text
id
login
email
password_hash
created_at
updated_at
```

### projects

Campos sugeridos:

```text
id
name
description
owner_id
total_size_bytes
documents_count
created_at
updated_at
deleted_at
```

### project_members

Campos sugeridos:

```text
project_id
user_id
role: owner | participant
created_at
```

### documents

Campos sugeridos:

```text
id
project_id
uploaded_by_id
filename
content_type
size_bytes
s3_bucket
s3_key
checksum_sha256
status: pending | available | failed | deleted
created_at
updated_at
```

### document_versions

Campos sugeridos:

```text
id
document_id
s3_key
size_bytes
version_number
created_at
```

### project_invites

Campos sugeridos:

```text
id
project_id
email
login
token_hash
role
expires_at
accepted_at
created_at
```

---

## 8. Normalización y denormalización

### Normalización obligatoria

Usar tablas separadas para:

- usuarios
- proyectos
- miembros de proyecto
- documentos

No guardar listas de usuarios o documentos como strings dentro de `projects`.

### Denormalización útil

Agregar campos calculados para mejorar consultas:

```text
projects.total_size_bytes
projects.documents_count
```

Estos campos pueden actualizarse cuando:

- se sube un documento
- se elimina un documento
- Lambda procesa un evento de S3
- se recalcula manualmente con un job de mantenimiento

---

## 9. Arquitectura interna recomendada

Usar separación por capas.

```text
app/
  main.py
  api/
    routes_auth.py
    routes_projects.py
    routes_documents.py
    routes_members.py
  core/
    config.py
    security.py
    exceptions.py
  db/
    session.py
    base.py
  models/
    user.py
    project.py
    document.py
  schemas/
    auth.py
    project.py
    document.py
  repositories/
    users.py
    projects.py
    documents.py
  services/
    auth_service.py
    project_service.py
    document_service.py
    storage_service.py
    permission_service.py
  storage/
    base.py
    local.py
    s3.py
  tests/
```

### Regla arquitectónica

No poner lógica de negocio directamente en los route handlers.

Route handlers deben:

1. Recibir request.
2. Validar schemas.
3. Obtener usuario actual.
4. Llamar servicios.
5. Devolver response schema.

Servicios deben:

1. Ejecutar reglas de negocio.
2. Validar permisos.
3. Coordinar repositories y storage.

Repositories deben:

1. Encapsular queries a base de datos.
2. No contener lógica de negocio pesada.

---

## 10. Storage abstraction

Crear una interfaz o clase base para storage.

```python
class StorageService:
    def upload(self, key: str, data: bytes, content_type: str) -> None:
        ...

    def download(self, key: str) -> bytes:
        ...

    def delete(self, key: str) -> None:
        ...

    def generate_presigned_upload_url(self, key: str, content_type: str) -> str:
        ...

    def generate_presigned_download_url(self, key: str) -> str:
        ...
```

Implementaciones:

```text
LocalStorageService
S3StorageService
```

Esto permite desarrollar localmente y migrar a S3 sin cambiar la lógica de negocio.

---

## 11. Deployment decision matrix

Escala:

- 1 = débil
- 3 = aceptable
- 5 = fuerte

| Criterio | Peso | AWS | On-premise / Self-hosted | Comentario |
|---|---:|---:|---:|---|
| Alineación con scope original | 15 | 5 | 3 | El scope ya incluye S3, Lambda y CI/CD cloud. |
| Relevancia profesional | 15 | 5 | 3 | AWS muestra cloud real. |
| Simplicidad operativa | 10 | 4 | 2 | AWS reduce administración de servidores; on-prem exige más mantenimiento. |
| Costo académico | 10 | 3 | 4 | On-prem puede ser más barato si ya existe hardware o VPS. |
| Facilidad de demo | 10 | 4 | 3 | AWS permite demo pública más directa. |
| File storage y eventos | 15 | 5 | 3 | S3 + Lambda encaja directo. |
| Seguridad y permisos | 10 | 4 | 3 | AWS ofrece IAM y servicios gestionados, pero requiere buena configuración. |
| Portabilidad | 5 | 3 | 5 | Docker Compose self-hosted es más portable. |
| Complejidad de implementación | 5 | 3 | 4 | AWS agrega IAM, roles, buckets y networking. |
| Valor para portfolio | 5 | 5 | 3 | AWS + CI/CD + S3/Lambda tiene más impacto profesional. |

### Resultado sugerido

| Opción | Score ponderado |
|---|---:|
| AWS | 430 / 500 |
| On-premise / Self-hosted | 325 / 500 |

### Decisión recomendada

Usar:

```text
Local development:
Docker Compose + PostgreSQL + local/S3-compatible storage adapter

Production target:
AWS ECS Fargate or App Runner + RDS PostgreSQL + S3 + Lambda

Backup deployment option:
On-premise Docker Compose + PostgreSQL + MinIO + worker
```

---

## 12. Arquitectura AWS recomendada

```text
Client
  ↓
FastAPI container
  ↓
ECS Fargate / App Runner
  ↓
PostgreSQL on RDS

Documents:
Client → presigned URL → S3
S3 event → Lambda → update document metadata / project total size

CI/CD:
GitHub Actions → tests/lint → build Docker image → push registry → deploy
```

### Servicios AWS sugeridos

| Componente | Servicio AWS |
|---|---|
| API | ECS Fargate, App Runner or Elastic Beanstalk |
| DB | RDS PostgreSQL |
| File storage | S3 |
| Event processing | Lambda triggered by S3 |
| Secrets | AWS Secrets Manager or SSM Parameter Store |
| Container registry | ECR or GitHub Container Registry |
| Logs | CloudWatch |
| CI/CD | GitHub Actions or GitLab CI |

---

## 13. Arquitectura on-premise recomendada

```text
Client
  ↓
Reverse proxy: Caddy / Nginx / Traefik
  ↓
FastAPI container
  ↓
PostgreSQL container or native PostgreSQL

Documents:
FastAPI → MinIO / local object storage

Background processing:
Celery/RQ/Arq worker → calculate file size / image resize
```

### Servicios on-premise sugeridos

| Componente | Tecnología |
|---|---|
| API | Docker container |
| DB | PostgreSQL |
| File storage | MinIO or filesystem |
| Event processing | Celery, RQ or Arq |
| Reverse proxy | Caddy, Traefik or Nginx |
| TLS | Caddy automatic HTTPS or reverse proxy config |
| CI/CD | GitHub Actions → SSH deploy / Docker pull |
| Backups | pg_dump + object storage backup |

---

## 14. Roadmap de desarrollo

Fecha de inicio sugerida: **martes 5 de mayo de 2026**  
Entrega final sugerida: **viernes 26 de junio de 2026**  
Duración: **8 semanas**

| Fase | Fechas | Scope | Entregable |
|---|---|---|---|
| 0 | May 5–May 8 | Diseño técnico y setup | Repo, arquitectura, DB draft, Docker local |
| 1 | May 11–May 15 | Auth + usuarios | Registro, login, JWT |
| 2 | May 18–May 22 | CRUD de proyectos | Crear, listar, ver, editar, borrar proyectos |
| 3 | May 25–May 29 | Permisos e invitaciones | Owner/participant, invite by login |
| 4 | Jun 1–Jun 5 | Documentos local/S3-ready | Upload, list, download, update, delete documents |
| 5 | Jun 8–Jun 12 | S3 + Lambda | Presigned URLs, S3 events, size calculation |
| 6 | Jun 15–Jun 19 | Tests + CI/CD | pytest, linting, Docker image, CI pipeline |
| 7 | Jun 22–Jun 26 | Deployment + hardening | AWS/on-prem deploy, docs, final demo |

---

## 15. Fase 0 - Setup y diseño técnico

Fechas: **May 5–May 8**

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
- README explica cómo correr local.
- ERD inicial documentado.

---

## 16. Fase 1 - Auth y usuarios

Fechas: **May 11–May 15**

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
- Validación con Pydantic.
- JWT con expiración de 1 hora.
- Dependency para usuario autenticado.
- Manejo de errores:
  - usuario duplicado
  - password inválido
  - token expirado
  - token inválido

### Entregables

- Registro funcional.
- Login funcional.
- JWT válido por 1 hora.
- Tests de auth.

### Definition of Done

- No se guarda password plano.
- Tests cubren login correcto e incorrecto.
- Endpoints protegidos rechazan requests sin JWT.

---

## 17. Fase 2 - CRUD de proyectos

Fechas: **May 18–May 22**

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
- Tests de permisos básicos.

### Definition of Done

- Usuario A no puede ver proyectos de Usuario B.
- Owner puede borrar.
- Usuario sin acceso recibe `403` o `404`, según decisión de diseño.
- Respuestas JSON consistentes.

---

## 18. Fase 3 - Roles, permisos e invitaciones

Fechas: **May 25–May 29**

### Objetivo

Implementar colaboración entre usuarios.

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

### Reglas

- Solo owner puede invitar.
- Solo owner puede quitar miembros.
- Participant puede modificar proyecto y documentos.
- Participant no puede borrar proyecto.
- Owner no puede eliminarse a sí mismo si es el único owner.

### Entregables

- Sistema de roles funcional.
- Tests de autorización.
- Matriz de permisos documentada.

---

## 19. Fase 4 - Documentos local/S3-ready

Fechas: **Jun 1–Jun 5**

### Objetivo

Completar la parte de documentos sin depender todavía de AWS.

### Endpoints

```http
GET    /projects/{project_id}/documents
POST   /projects/{project_id}/documents
GET    /documents/{document_id}
PUT    /documents/{document_id}
DELETE /documents/{document_id}
```

### Scope

- Solo aceptar `.pdf` y `.docx`.
- Validar `content_type`.
- Guardar metadata en PostgreSQL.
- Guardar archivo localmente o con adaptador compatible S3.
- Validar acceso por proyecto.
- Al borrar documento, borrar metadata y objeto físico.

### Entregables

- CRUD completo de documentos.
- Tabla `documents`.
- Servicio de storage abstracto.

---

## 20. Fase 5 - S3 + Lambda + límites de almacenamiento

Fechas: **Jun 8–Jun 12**

### Objetivo

Implementar la parte cloud del scope.

### Scope

- Crear bucket S3.
- Implementar presigned upload/download.
- Guardar documentos con `s3_key`.
- Configurar Lambda para eventos de S3.
- Cuando se sube archivo:
  - calcular tamaño
  - actualizar `documents.size_bytes`
  - actualizar `projects.total_size_bytes`
  - opcional: generar thumbnail/preview si es imagen
- Aplicar límite de storage por proyecto.

### Endpoints sugeridos

```http
POST /projects/{project_id}/documents/presign-upload
POST /projects/{project_id}/documents/complete-upload
GET  /documents/{document_id}/download-url
```

### Entregables

- S3 funcional.
- Lambda funcional.
- Metadata actualizada desde evento.
- Límite de tamaño por proyecto.

### Definition of Done

- Un archivo subido a S3 genera evento.
- Lambda procesa evento.
- DB refleja tamaño actualizado.
- Proyecto rechaza nuevos uploads si supera límite.

---

## 21. Fase 6 - Testing, calidad y CI/CD

Fechas: **Jun 15–Jun 19**

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

- Ruff lint.
- Ruff format.
- mypy opcional.
- Coverage report.
- Alembic migrations.
- CI en pull request.

### Pipeline mínimo

```text
on pull request:
  - install dependencies
  - lint
  - format check
  - run tests
  - build Docker image

on merge to main:
  - build image
  - push image
  - deploy
```

### Entregables

- GitHub Actions o GitLab CI funcional.
- Docker image publicada.
- Tests automáticos.
- Badge en README.

---

## 22. Fase 7 - Deployment, documentación y demo final

Fechas: **Jun 22–Jun 26**

### Objetivo

Cerrar el proyecto como entrega presentable.

### Scope AWS

- Deploy API.
- Deploy DB.
- Configurar variables de entorno.
- Configurar bucket.
- Configurar Lambda.
- Configurar logs.
- Crear usuario demo.
- Probar flujo completo.

### Scope documentación

- README final.
- Diagrama de arquitectura.
- ERD.
- API examples.
- Decisiones técnicas.
- Cómo correr local.
- Cómo desplegar.
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
9. Try deleting project as participant → should fail
10. Delete project as owner → should succeed
```

---

## 23. MVP vs stretch goals

### MVP obligatorio

Debe estar listo máximo el **viernes 5 de junio de 2026**.

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

Debe estar listo máximo el **viernes 12 de junio de 2026**.

```text
- S3 storage
- Presigned URLs
- Lambda triggered by S3 event
- File size calculation
- Project total storage calculation
```

### Scope profesional

Debe estar listo máximo el **viernes 19 de junio de 2026**.

```text
- CI pipeline
- Linting
- Tests
- Docker image build
- Alembic migrations
- README usable
```

### Stretch goals

Solo hacer después del MVP.

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

---

## 24. Backlog por prioridad

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

---

## 25. Convenciones de implementación

### Status codes sugeridos

| Caso | Status code |
|---|---:|
| Creación exitosa | 201 |
| Lectura exitosa | 200 |
| Actualización exitosa | 200 |
| Eliminación exitosa | 204 |
| Request inválido | 400 |
| Auth requerida | 401 |
| Sin permisos | 403 |
| Recurso no encontrado | 404 |
| Conflicto, duplicado | 409 |
| Validación fallida | 422 |

### Manejo de errores

Usar formato consistente:

```json
{
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "message": "Project not found or user has no access.",
    "details": null
  }
}
```

### Naming

- Usar endpoints en plural: `/projects`, `/documents`.
- Usar `PATCH` para actualización parcial de project info.
- Usar `POST` para acciones que generan estado, como invites.
- No usar `GET` para crear invitaciones o enviar emails.

---

## 26. Reglas para asistentes LLM que trabajen en este repo

Cuando un LLM ayude a implementar este proyecto, debe seguir estas reglas:

1. Mantener el scope del proyecto.
2. No cambiar el stack principal sin justificarlo.
3. Priorizar primero MVP, luego cloud, luego extras.
4. No poner lógica de negocio pesada dentro de los route handlers.
5. Mantener separación entre schemas, models, services y repositories.
6. Usar Pydantic para request/response validation.
7. Usar SQLAlchemy/Alembic para DB y migraciones.
8. Usar JWT en todos los endpoints de negocio.
9. Validar permisos por proyecto en cada operación sensible.
10. No exponer documentos a usuarios sin acceso al proyecto.
11. No guardar passwords en texto plano.
12. No subir archivos sin validar extensión y content type.
13. No bloquear el MVP por features opcionales.
14. Escribir tests para auth, permisos, proyectos y documentos.
15. Mantener respuestas JSON consistentes.
16. Documentar decisiones importantes en README o `/docs`.

---

## 27. Checklist final de entrega

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
[ ] documentos respetan permisos del proyecto
[ ] se aceptan solo pdf/docx en MVP
[ ] metadata de documentos se guarda en DB
[ ] S3/presigned URL funciona si aplica
[ ] Lambda actualiza size metadata si aplica
[ ] tests pasan localmente
[ ] CI corre lint + tests
[ ] README explica setup local
[ ] README explica deployment
[ ] ERD incluido
[ ] demo script incluido
```

---

## 28. Entrega final recomendada

El repo debería incluir:

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

