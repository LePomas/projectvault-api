---
title: "ProjectVault - Product Spec"
version: "1.0"
language: "es-MX"
last_updated: "2026-05-13"
purpose: "Descripcion funcional, reglas de negocio, permisos y modelo de dominio objetivo para ProjectVault."
---

# Product Spec

> Este documento es especificacion de producto y dominio objetivo. No representa
> necesariamente el estado implementado. Para convenciones de API, usar
> `docs/API_CONVENTIONS.md`.

## Objetivo

Construir un servicio backend llamado **ProjectVault**: una API segura para
crear, actualizar, compartir y eliminar informacion de proyectos, incluyendo
detalles del proyecto y documentos adjuntos.

El sistema debe permitir que usuarios registrados creen proyectos, suban
documentos, inviten a otros usuarios y controlen permisos por proyecto.

## Funcionalidad obligatoria

El sistema debe permitir:

1. Registrar usuarios.
2. Iniciar sesion.
3. Emitir JWT valido por 1 hora.
4. Crear proyectos.
5. Listar proyectos accesibles por usuario.
6. Ver detalles de un proyecto.
7. Actualizar nombre y descripcion de un proyecto.
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

## Funcionalidad opcional

1. Enviar invitacion por email.
2. Generar link de invitacion con token hasheado.
3. Aceptar invitacion desde browser.
4. Redimensionar imagenes con Lambda.
5. Calcular tamano total de archivos por proyecto.
6. Aplicar limite de almacenamiento por proyecto.
7. Versionado de documentos.
8. Audit log.
9. Soft delete.
10. PostgreSQL Row-Level Security.
11. Terraform/OpenTofu.

## API recomendada

Usar nombres REST consistentes en plural. Las convenciones de status codes,
errores y naming viven en `docs/API_CONVENTIONS.md`.

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
PATCH  /documents/{document_id}
DELETE /documents/{document_id}
```

### S3 presigned flow, recomendado para produccion

```http
POST /projects/{project_id}/documents/presign-upload
POST /projects/{project_id}/documents/complete-upload
GET  /documents/{document_id}/download-url
```

## Reglas de negocio

### Usuarios

- Cada usuario tiene login unico.
- Las contrasenas nunca se guardan en texto plano.
- El login devuelve un JWT.
- El JWT debe expirar en 1 hora.
- Todos los endpoints de negocio deben requerir JWT.

### Proyectos

- Al crear un proyecto, el usuario creador se convierte automaticamente en `owner`.
- Un proyecto puede tener multiples usuarios asociados.
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
- El archivo fisico debe guardarse localmente, en S3 o en un storage compatible.

### Invitaciones

- Solo owner puede invitar usuarios.
- La invitacion por login asigna rol `owner` o `participant`.
- Invitar `owner` concede permisos administrativos completos sobre el proyecto.
- Un proyecto debe conservar al menos un owner.
- Participant no puede invitar a otros usuarios.
- Participant no puede eliminar el proyecto.

## Matriz de permisos

| Accion | Owner | Participant | No member |
|---|---:|---:|---:|
| Ver proyecto | Si | Si | No |
| Editar proyecto | Si | Si | No |
| Eliminar proyecto | Si | No | No |
| Ver documentos | Si | Si | No |
| Subir documentos | Si | Si | No |
| Actualizar documentos | Si | Si | No |
| Eliminar documentos | Si | Si | No |
| Invitar owners | Si | No | No |
| Invitar participants | Si | No | No |
| Quitar usuarios | Si | No | No |

## Modelo de base de datos recomendado

### Tablas minimas

```text
users
projects
project_members
documents
```

### Tablas recomendadas para version profesional

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
role: owner | participant
expires_at
accepted_at
created_at
```

## Normalizacion y denormalizacion

### Normalizacion obligatoria

Usar tablas separadas para:

- usuarios
- proyectos
- miembros de proyecto
- documentos

No guardar listas de usuarios o documentos como strings dentro de `projects`.

### Denormalizacion util

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
