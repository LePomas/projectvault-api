---
title: "ProjectVault - Project Plan Index"
version: "1.1"
language: "es-MX"
last_updated: "2026-06-01"
purpose: "Indice compacto para encontrar contexto de producto, arquitectura objetivo y roadmap sin cargar todo el plan completo."
---

# ProjectVault - Índice del plan

> Este documento describe dirección, arquitectura objetivo y roadmap. No
> representa necesariamente el estado implementado del repositorio. El código,
> `README.md`, `AGENTS.md`, `docs/API_CONVENTIONS.md` y `docs/ERD.md` son las
> fuentes que deben revisarse para confirmar el estado actual.

## Objetivo del proyecto

Construir un servicio backend llamado **ProjectVault**: una API segura para
crear, actualizar, compartir y eliminar información de proyectos, incluyendo
detalles del proyecto y documentos adjuntos.

El sistema debe permitir que usuarios registrados creen proyectos, suban
documentos, inviten a otros usuarios y controlen permisos por proyecto. El
alcance puede incluir storage compatible con S3, deployment cloud o self-hosted
y automatización, pero solo como target hasta que el código lo confirme.

## Como leer estos documentos

Abrir solo el documento necesario para la tarea:

| Necesidad | Documento |
|---|---|
| Estado implementado, setup local y comandos básicos | `README.md` |
| Reglas operativas para agentes y convenciones del repo | `AGENTS.md` |
| Convenciones de API, status codes y formato de errores | `docs/API_CONVENTIONS.md` |
| ERD actual documentado | `docs/ERD.md` |
| Requisitos funcionales, reglas de negocio y permisos objetivo | `docs/PRODUCT_SPEC.md` |
| Arquitectura objetivo, storage y opciones de deployment | `docs/TARGET_ARCHITECTURE.md` |
| Decision MinIO vs SeaweedFS para Fase 5 | `docs/STORAGE_DECISION_MATRIX.md` |
| Fases, prioridades, MVP, backlog y checklist de entrega | `docs/ROADMAP.md` |

## Current vs target

ProjectVault ya tiene una base FastAPI con SQLAlchemy, JWT, PostgreSQL en
Docker Compose, pruebas con SQLite en memoria, CI de GitHub Actions y un
baseline inicial de Alembic. Para confirmar que algo existe, revisar el código
y `README.md`; este plan puede mencionar fases futuras u opciones no
implementadas.

Algunas capacidades en los documentos divididos son objetivo o roadmap, no
garantía de implementación actual. En particular, no asumir que existen S3,
Lambda, CI/CD, Alembic, deployment cloud o features opcionales hasta verificarlo
en el código. El estado actual verificado es: MinIO/S3-compatible local y un
handler estilo Lambda existen; GitHub Actions CI existe; el workflow de GitHub
Actions CD existe para recursos AWS precreados; Alembic tiene baseline inicial.
La preparacion AWS live es parcial: ECR, bucket S3, OIDC y JWT secret existen;
RDS, `DATABASE_URL`, ECS, Lambda, imagenes ECR, permisos finales, ambiente
desplegado real y migraciones posteriores al baseline siguen pendientes.

## Documentos divididos

- `docs/PRODUCT_SPEC.md`: descripción funcional, reglas de negocio, matriz de
  permisos, modelo de datos recomendado y notas de normalización.
- `docs/TARGET_ARCHITECTURE.md`: stack objetivo, alternativas aceptables,
  arquitectura interna, abstracción de storage y opciones AWS/on-premise.
- `docs/STORAGE_DECISION_MATRIX.md`: comparacion MinIO vs SeaweedFS para el
  desarrollo local/self-hosted de Fase 5.
- `docs/ROADMAP.md`: roadmap de fases, MVP vs stretch goals, backlog por
  prioridad, checklist final y contenido recomendado de entrega.

## Qué no contiene este índice

Este archivo evita cargar bloques largos que antes vivían en un solo documento.
En particular, aquí no deben agregarse:

- Tablas completas de roadmap por fase.
- Checklists de entrega final.
- Matrices detalladas de deployment.
- Diagramas o listas completas de servicios cloud.
- Modelos de base de datos campo por campo.
- Convenciones de API duplicadas desde `docs/API_CONVENTIONS.md`.
- Reglas operativas de agentes duplicadas desde `AGENTS.md`.

Si alguno de esos temas necesita cambiar, editar el documento especializado
correspondiente y mantener este índice como una ruta de lectura.

## Rutas de lectura recomendadas

| Tarea | Leer después de `AGENTS.md` |
|---|---|
| Endpoints o errores | `docs/API_CONVENTIONS.md` y código en `app/api/` |
| Producto o permisos | `docs/PRODUCT_SPEC.md` y servicios/tests relevantes |
| Arquitectura futura | `docs/TARGET_ARCHITECTURE.md` y código existente |
| Planeación | `docs/ROADMAP.md` y `README.md` |

## Guia rapida para agentes

- Usar `AGENTS.md` para reglas de trabajo, comandos y límites del repo.
- Usar `docs/API_CONVENTIONS.md` para diseñar o revisar endpoints.
- Usar `docs/PRODUCT_SPEC.md` solo cuando la tarea requiera reglas de producto,
  permisos o modelo de dominio objetivo.
- Usar `docs/TARGET_ARCHITECTURE.md` solo cuando la tarea trate de arquitectura,
  storage o deployment futuro.
- Usar `docs/ROADMAP.md` solo cuando la tarea sea de planeación, priorización o
  seguimiento de entrega.
- No tratar `docs/ROADMAP.md` ni `docs/TARGET_ARCHITECTURE.md` como estado
  implementado.

## Mantenimiento

Mantener este archivo corto. Si una sección empieza a necesitar detalles,
moverla a uno de los documentos especializados.

Cuando el código cambie el comportamiento real del sistema, actualizar primero
las fuentes operativas (`README.md`, `AGENTS.md`, `docs/API_CONVENTIONS.md`,
`docs/ERD.md` o tests relevantes). Después, ajustar el plan solo si cambia la
dirección futura.

Cuando el roadmap cambie sin tocar código, actualizar `docs/ROADMAP.md` y dejar
este índice estable salvo que cambien las rutas de lectura.

## Fuentes de verdad practicas

| Tema | Fuente principal |
|---|---|
| Código ejecutable | `app/`, `tests/`, `db/init/001_initial_schema.sql` |
| Setup local | `README.md` |
| CI actual | `.github/workflows/ci.yml` |
| Migraciones | `alembic/versions/`, `db/init/001_initial_schema.sql` |
| Reglas de agentes | `AGENTS.md` |
| API y errores | `docs/API_CONVENTIONS.md` |
| Esquema actual documentado | `docs/ERD.md` |
| Plan y alcance futuro | `docs/ROADMAP.md` |
