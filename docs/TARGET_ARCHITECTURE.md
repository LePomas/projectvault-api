---
title: "ProjectVault - Target Architecture"
version: "1.0"
language: "es-MX"
last_updated: "2026-06-01"
purpose: "Arquitectura objetivo, stack recomendado, storage y deployment futuro para ProjectVault."
---

# Target Architecture

> Este documento describe arquitectura objetivo. No asumir que S3, Lambda,
> Alembic, CI/CD o deployment cloud estan implementados sin verificar el codigo.
> Estado actual verificado: CI de GitHub Actions existe para lint, format check,
> tests y `docker compose config`; el workflow de CD existe en el repo para
> publicar imagenes en ECR, desplegar la API a un servicio ECS existente y
> actualizar una Lambda existente por imagen. Alembic tiene baseline inicial;
> MinIO local, adaptador S3-compatible y handler estilo Lambda existen. La
> preparacion AWS live ya incluye ECR con imagenes, bucket S3 de produccion,
> OIDC, permisos de deploy, secrets JWT y `DATABASE_URL`, RDS PostgreSQL, ECS
> service, Lambda por imagen, notificacion S3 ObjectCreated y un primer workflow
> Deploy exitoso. Siguen pendientes el ingress publico/API domain, frontend
> productivo, IaC y migraciones posteriores al baseline.

## Stack recomendado

### Stack base

| Area | Tecnologia recomendada |
|---|---|
| Lenguaje | Python 3.12+ |
| API | FastAPI |
| Validacion | Pydantic v2 |
| Base de datos | PostgreSQL |
| ORM | SQLAlchemy 2.x |
| Migraciones | Alembic |
| Driver PostgreSQL | psycopg 3 |
| Auth | JWT, expiracion de 1 hora |
| Storage cloud | AWS S3 |
| Procesamiento de eventos | AWS Lambda triggered by S3 event |
| Desarrollo local | Docker Compose |
| Testing | pytest |
| Calidad | Ruff, optional mypy |
| Packaging | uv or Poetry |
| CI/CD | GitHub Actions |

### Alternativas aceptables

| Area | Alternativa |
|---|---|
| ORM | SQLModel, si se prioriza velocidad sobre control fino |
| Storage local | Local filesystem adapter |
| Storage self-hosted | MinIO para Fase 5 local; ver `docs/STORAGE_DECISION_MATRIX.md` para MinIO vs SeaweedFS |
| Background jobs on-premise | Celery, RQ, Arq |
| Deployment AWS | ECS Fargate, App Runner, Elastic Beanstalk |
| Deployment self-hosted | Docker Compose + VPS + reverse proxy |
| Reverse proxy | Caddy, Nginx, Traefik |

## Arquitectura interna recomendada

Usar separacion por capas.

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

### Regla arquitectonica

No poner logica de negocio directamente en los route handlers.

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
2. No contener logica de negocio pesada.

## Storage abstraction

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

Esto permite desarrollar localmente y migrar a S3 sin cambiar la logica de negocio.

## Deployment decision matrix

Escala:

- 1 = debil
- 3 = aceptable
- 5 = fuerte

| Criterio | Peso | AWS | On-premise / Self-hosted | Comentario |
|---|---:|---:|---:|---|
| Alineacion con scope original | 15 | 5 | 3 | El scope ya incluye S3, Lambda y CI/CD cloud. |
| Relevancia profesional | 15 | 5 | 3 | AWS muestra cloud real. |
| Simplicidad operativa | 10 | 4 | 2 | AWS reduce administracion de servidores; on-prem exige mas mantenimiento. |
| Costo academico | 10 | 3 | 4 | On-prem puede ser mas barato si ya existe hardware o VPS. |
| Facilidad de demo | 10 | 4 | 3 | AWS permite demo publica mas directa. |
| File storage y eventos | 15 | 5 | 3 | S3 + Lambda encaja directo. |
| Seguridad y permisos | 10 | 4 | 3 | AWS ofrece IAM y servicios gestionados, pero requiere buena configuracion. |
| Portabilidad | 5 | 3 | 5 | Docker Compose self-hosted es mas portable. |
| Complejidad de implementacion | 5 | 3 | 4 | AWS agrega IAM, roles, buckets y networking. |
| Valor para portfolio | 5 | 5 | 3 | AWS + CI/CD + S3/Lambda tiene mas impacto profesional. |

### Resultado sugerido

| Opcion | Score ponderado |
|---|---:|
| AWS | 430 / 500 |
| On-premise / Self-hosted | 325 / 500 |

### Decision recomendada

Usar:

```text
Local development:
Docker Compose + PostgreSQL + local/S3-compatible storage adapter

Production target:
AWS ECS Fargate or App Runner + RDS PostgreSQL + S3 + Lambda

Backup deployment option:
On-premise Docker Compose + PostgreSQL + MinIO + worker
```

## Arquitectura AWS recomendada

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
GitHub Actions CI → tests/lint/format check → Compose config validation
GitHub Actions CD → build images → push ECR
GitHub Actions CD → deploy existing ECS service
GitHub Actions CD → update existing Lambda function
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
| CI/CD | GitHub Actions |

## Arquitectura on-premise recomendada

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

| Componente | Tecnologia |
|---|---|
| API | Docker container |
| DB | PostgreSQL |
| File storage | MinIO or filesystem |
| Event processing | Celery, RQ or Arq |
| Reverse proxy | Caddy, Traefik or Nginx |
| TLS | Caddy automatic HTTPS or reverse proxy config |
| CI/CD | GitHub Actions → SSH deploy / Docker pull |
| Backups | pg_dump + object storage backup |
