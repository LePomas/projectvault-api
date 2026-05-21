---
title: "ProjectVault - Storage Decision Matrix"
version: "1.0"
language: "es-MX"
last_updated: "2026-05-21"
purpose: "Comparacion de MinIO y SeaweedFS para el desarrollo de la siguiente fase de storage S3-compatible."
---

# Storage Decision Matrix

> Este documento es una decision de arquitectura para Fase 5. No significa que
> MinIO, SeaweedFS, S3, Lambda o URLs presignadas ya esten implementadas.

## Contexto

ProjectVault ya tiene Fase 4 con storage local y descarga servida por el
backend. La siguiente fase necesita preparar el flujo S3-compatible:

- upload/download con URLs presignadas
- una abstraccion formal de storage
- metadata de documentos sincronizada con el storage
- limites de almacenamiento por proyecto
- compatibilidad futura con AWS S3/Lambda

La decision aqui es que servicio conviene usar durante desarrollo local y
self-hosted para probar el contrato S3-compatible antes de mover el target
principal a AWS S3.

## Opciones comparadas

### MinIO

MinIO Community es un object store S3-compatible bajo licencia AGPLv3. MinIO
AIStor es la linea comercial actual y documenta S3 nativo, despliegues en
Kubernetes, Linux, contenedor, macOS y Windows.

Fortalezas para ProjectVault:

- Modelo mental cercano a AWS S3.
- Bueno para validar clientes S3, buckets, keys, multipart y presigned URLs.
- Integracion simple con SDKs S3-compatible.
- Menor desviacion respecto al roadmap actual, que apunta a S3.

Riesgos:

- AGPLv3 en Community puede ser incomoda si el proyecto se reutiliza en un
  contexto comercial o cerrado.
- La documentacion principal actual empuja AIStor/comercial, asi que hay que
  separar claramente uso local de Community vs target cloud AWS.

### SeaweedFS

SeaweedFS es un sistema distribuido para object storage S3, file systems e
Iceberg tables. Su repositorio declara licencia Apache-2.0 y ofrece un modo
`weed mini`/Docker para levantar un endpoint S3 local rapidamente.

Fortalezas para ProjectVault:

- Licencia Apache-2.0 mas permisiva.
- Un solo sistema puede exponer S3, FUSE/WebDAV/HDFS y storage distribuido.
- Buen fit si el proyecto evoluciona hacia self-hosted fuerte o muchos archivos.
- Quickstart local sencillo.

Riesgos:

- Es mas amplio que el problema actual; puede introducir conceptos operativos
  innecesarios para una API que solo necesita S3-compatible.
- Para Fase 5, el objetivo no es reemplazar filesystem/POSIX ni HDFS, sino
  validar el contrato S3 y luego poder migrar a AWS S3.
- Algunas capacidades de proteccion operativa avanzadas aparecen en la linea
  Enterprise, no en el baseline open source.

## Matriz ponderada

Escala:

- 1 = debil
- 3 = aceptable
- 5 = fuerte

| Criterio | Peso | MinIO | SeaweedFS | Comentario |
|---|---:|---:|---:|---|
| Alineacion con Fase 5 S3/presigned | 20 | 5 | 4 | Ambos exponen S3; MinIO esta mas centrado en object storage S3. |
| Portabilidad futura a AWS S3 | 15 | 5 | 4 | MinIO minimiza desviacion conceptual respecto a S3. |
| Simplicidad para Docker Compose local | 15 | 5 | 4 | MinIO suele ser directo como bucket local; SeaweedFS tambien tiene modo rapido pero trae mas superficies. |
| Compatibilidad con SDKs S3 | 15 | 5 | 4 | Para ProjectVault importa usar `boto3`/cliente S3 con endpoint configurable. |
| Complejidad operativa self-hosted | 10 | 4 | 3 | SeaweedFS escala a mas modos, pero eso tambien aumenta decisiones operativas. |
| Licencia y reutilizacion | 10 | 2 | 5 | MinIO Community es AGPLv3; SeaweedFS es Apache-2.0. |
| Documentacion y ecosistema para object storage | 5 | 4 | 3 | MinIO es muy conocido para S3-compatible; docs actuales mezclan Community/AIStor. |
| Fit para muchos archivos / filesystem adicional | 5 | 3 | 5 | SeaweedFS destaca si tambien se necesita FUSE/WebDAV/HDFS o escalado horizontal de archivos. |
| Riesgo de sobreingenieria para esta API | 5 | 5 | 3 | ProjectVault no necesita filesystem distribuido en Fase 5. |

### Score ponderado

| Opcion | Score ponderado |
|---|---:|
| MinIO | 445 / 500 |
| SeaweedFS | 395 / 500 |

## Decision recomendada

Usar **MinIO para el desarrollo local de Fase 5** como backend S3-compatible
temporal, con una interfaz de storage que no dependa de MinIO directamente.

La implementacion debe usar un cliente S3 configurable por variables de entorno:

```text
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET=projectvault-documents
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_REGION=us-east-1
```

El codigo debe hablar con la API S3-compatible, no con APIs propias de MinIO.
Asi el mismo adaptador puede apuntar despues a AWS S3 quitando
`S3_ENDPOINT_URL` o cambiando configuracion, sin reescribir servicios de
documentos.

## Cuando elegir SeaweedFS

SeaweedFS seria mejor si cambia una de estas condiciones:

- el deployment principal pasa a ser self-hosted, no AWS;
- se necesita una licencia permisiva para distribuir el stack completo;
- se necesita exponer tambien filesystem/FUSE/WebDAV/HDFS;
- se espera una carga dominante de muchisimos archivos pequenos;
- se quiere evaluar una plataforma de storage distribuido, no solo un reemplazo
  local de S3.

## Consecuencias para Fase 5

Implementar la fase en este orden:

1. Crear `StorageService` formal con metodos para upload, delete y URLs
   presignadas.
2. Mantener `LocalDocumentStorage` para Fase 4 y tests existentes.
3. Agregar `S3DocumentStorage` usando cliente S3-compatible.
4. Configurar MinIO solo en Docker Compose/desarrollo local.
5. Agregar endpoints:

```http
POST /projects/{project_id}/documents/presign-upload
POST /projects/{project_id}/documents/complete-upload
GET  /documents/{document_id}/download-url
```

6. Dejar Lambda/eventos como target AWS; para local, simular el evento desde
   `complete-upload` o un worker simple si hace falta.

## Fuentes consultadas

- MinIO GitHub README: https://github.com/minio/minio
- MinIO AIStor docs: https://docs.min.io/aistor/
- SeaweedFS GitHub README: https://github.com/seaweedfs/seaweedfs
- SeaweedFS product/docs page: https://seaweedfs.com/docs/
