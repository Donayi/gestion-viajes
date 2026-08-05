# Constitución Técnica — Gestión de Viajes DAFREQ

> **Documento maestro y memoria técnica permanente del proyecto.** Esta es la referencia obligatoria para cualquier desarrollo realizado por personas o IA. Debe consultarse antes de analizar, proponer o ejecutar cambios.

## Propósito y autoridad del documento

`AI_CONTEXT.md` concentra el contexto verificable del sistema, sus reglas de negocio, arquitectura vigente, restricciones y procedimiento oficial de trabajo. No sustituye al código como fuente de verdad técnica ni a la decisión humana como fuente de autorización. Cuando este documento y el código difieran, se debe detener el cambio, documentar la discrepancia y solicitar criterio humano; nunca se debe resolver inventando una regla.

Este documento debe actualizarse cuando un cambio aprobado altere arquitectura, contratos, modelos, reglas de negocio, infraestructura, módulos, riesgos o procedimientos. Una actualización documental no autoriza por sí misma cambios funcionales.

## Índice

- [Proyecto](#proyecto)
- [Filosofía del Proyecto](#filosofía-del-proyecto)
- [Arquitectura](#arquitectura)
- [Principios Arquitectónicos](#principios-arquitectónicos)
- [Arquitectura Protegida](#arquitectura-protegida)
- [Stack tecnológico](#stack-tecnológico)
- [Reglas de negocio](#reglas-de-negocio)
- [Módulos existentes](#módulos-existentes)
- [API](#api)
- [Dashboard](#dashboard)
- [Frontend](#frontend)
- [Backend](#backend)
- [Base de datos](#base-de-datos)
- [Docker](#docker)
- [Convenciones](#convenciones)
- [Buenas Prácticas](#buenas-prácticas)
- [Errores que Deben Evitarse](#errores-que-deben-evitarse)
- [Riesgos técnicos](#riesgos-técnicos)
- [Pendientes técnicos](#pendientes-técnicos)
- [Cómo Trabajar en este Proyecto](#cómo-trabajar-en-este-proyecto)
- [Reglas para IA](#reglas-para-ia)
- [Flujo Oficial ChatGPT + Codex](#flujo-oficial-chatgpt--codex)
- [Checklist Antes de Modificar Código](#checklist-antes-de-modificar-código)
- [Checklist Antes de Terminar una Tarea](#checklist-antes-de-terminar-una-tarea)
- [Roadmap](#roadmap)
- [Changelog IA](#changelog-ia)
- [Lecciones Aprendidas](#lecciones-aprendidas)
- [Historial técnico](#historial-técnico)

---

# Proyecto

## Nombre

**Gestión de Viajes / Plataforma Logística DAFREQ**. El paquete del frontend se identifica como `gestion-viajes-frontend` y la interfaz usa el nombre “Centro operativo DAFREQ”. No se encontró una denominación formal adicional.

## Objetivo del sistema

Centralizar la operación de viajes de transporte: alta y asignación de viajes, seguimiento de su estado, captura de eventos y ubicación, administración de recursos, evidencias y documentos, mantenimiento de unidades, indicadores, alertas y notificaciones.

## Problema de negocio

Evita la asignación simultánea de operadores, tráilers y cajas; conserva trazabilidad del ciclo de un viaje; controla requisitos documentales; muestra disponibilidad operativa; y concentra información para decisiones administrativas y trabajo móvil en campo.

## Usuarios

- **Administración (`ADMIN` y roles cuyo nombre inicia con `ADMIN_`)**: gestión integral, catálogos, viajes, dashboard, documentación, alertas y configuración operativa.
- **Operadores (`OPERADOR`)**: consulta y operación de viajes propios, captura de eventos, ubicación y evidencias.
- **Mantenimiento (`MANTENIMIENTO`)**: gestión de órdenes de mantenimiento mediante una interfaz específica.

No se encontraron otros perfiles funcionales implementados.

## Estado actual

Aplicación full-stack funcional, con API, interfaz protegida por roles, persistencia relacional, PWA, dashboard administrativo y de operador, mapas, mantenimiento, documentos, alertas e integraciones opcionales. La suite backend contiene pruebas de contrato, seguridad, smoke y persistencia aislada en PostgreSQL. Los cambios incluidos en el commit `baf5a31` fueron validados antes de crear el commit mediante `infra/compose.test.yml`, con resultado de 128 pruebas aprobadas, 0 fallidas y 0 errores. No hay sistema de migraciones versionadas; el esquema se crea y ajusta en el arranque. Existen áreas parciales indicadas en [Pendientes técnicos](#pendientes-técnicos).

---

# Filosofía del Proyecto

Los siguientes principios gobiernan la evolución del sistema. Constituyen normas de trabajo del proyecto; no se presentan como motivaciones históricas comprobadas cuando el repositorio no documenta su origen.

1. **Seguridad antes que velocidad**: proteger autenticación, autorización, secretos, datos y aislamiento entre operadores tiene prioridad sobre entregar cambios apresurados.
2. **Cambios pequeños y verificables**: cada tarea debe tener alcance explícito, pocos archivos y una consecuencia comprensible.
3. **Compatibilidad por defecto**: conservar contratos públicos, datos existentes y comportamiento observable salvo autorización expresa para romperlos.
4. **No romper funcionalidades existentes**: antes de cambiar una regla compartida se deben identificar todos sus consumidores y validaciones autorizadas.
5. **Claridad sobre complejidad**: preferir código directo, nombres consistentes y separación de responsabilidades a abstracciones prematuras.
6. **Mantenibilidad**: reutilizar módulos y patrones existentes, limitar duplicación y registrar decisiones que afecten el futuro.
7. **Deuda técnica explícita**: no ocultar atajos; documentar riesgos, alcance y seguimiento cuando una solución temporal sea autorizada.
8. **Reglas de negocio como invariantes**: no asumir ni reinterpretar disponibilidad, estados, permisos, evidencia o liberación de recursos.
9. **Trazabilidad**: explicar qué cambió, por qué, qué impacto tiene y cómo fue validado.
10. **Revisión humana obligatoria**: ninguna intervención de IA se considera aceptada hasta que una persona la revise.

---

# Arquitectura

## Frontend

Aplicación Next.js con App Router, React y TypeScript. Las rutas se dividen en grupos públicos y protegidos. La sesión JWT se conserva en el navegador y se valida contra `GET /auth/me`. Los accesos se filtran mediante guards y navegación por rol. La UI es responsive, con experiencia móvil específica para operadores y mapas Leaflet cargados desde componentes cliente.

## Backend

API REST síncrona con FastAPI, Pydantic y SQLAlchemy. La composición se realiza mediante una fábrica de aplicación y módulos de bootstrap para CORS, routers, esquema, seeds y tareas de inicio. Los routers delegan persistencia y reglas a `crud/`; las dependencias resuelven sesión de base de datos, autenticación y autorización.

## Base de datos

PostgreSQL 16 mediante el driver `psycopg`. SQLAlchemy define el modelo relacional. La disponibilidad se calcula dinámicamente a partir de viajes, asignaciones y mantenimientos; no se almacena como un estado duplicado.

## Infraestructura

La infraestructura versionada se limita a Docker Compose, Dockerfiles, scripts locales y un ejemplo de NGINX. Producción contempla PostgreSQL y FastAPI en contenedores; la API escucha en `127.0.0.1:8080` para quedar detrás de NGINX. El despliegue del frontend/PM2 aparece documentado, pero PM2 no está definido como servicio en los archivos Compose.

## Docker

- `backend/Dockerfile`: imagen de backend para ejecución normal.
- `backend/Dockerfile.dev`: backend de desarrollo con recarga.
- `infra/compose.yml`: DB interna y API con bind mount del backend.
- `infra/compose.dev.yml`: DB publicada en `5432`, API en `127.0.0.1:8080` y volumen de desarrollo independiente.
- `infra/compose.prod.yml`: DB interna y API sin bind mount, ambas con política `unless-stopped`.

## Servicios externos

- **Cloudflare R2/S3 compatible**: URLs prefirmadas y metadatos de archivos mediante `boto3`; integración condicionada por variables de entorno.
- **Telegram Bot API**: destinatarios, prueba y envío de alertas pendientes; puede deshabilitarse.
- **Web Push**: suscripciones PWA, VAPID y pruebas de notificación mediante `pywebpush`; puede deshabilitarse.
- **Leaflet/OpenStreetMap**: representación cartográfica en el frontend. No se encontró un proveedor comercial de geocodificación configurado.
- **NGINX y PM2**: previstos para despliegue según archivos de infraestructura/documentación, no como dependencias de la aplicación.

## Estructura general

```text
gestion-viajes/
├── backend/
│   ├── app/
│   │   ├── api/          # Routers y dependencias HTTP
│   │   ├── bootstrap/    # Fábrica, CORS, esquema, seeds y startup
│   │   ├── core/         # Configuración, seguridad y R2
│   │   ├── crud/         # Acceso a datos y reglas de negocio
│   │   ├── db/           # Engine, sesión, Base y dependencias
│   │   ├── models/       # Modelos SQLAlchemy
│   │   ├── schemas/      # Contratos Pydantic
│   │   ├── seeds/        # Catálogos y datos iniciales
│   │   └── services/     # Telegram y Web Push
│   ├── scripts/          # Utilidades (claves VAPID)
│   └── tests/            # Pruebas de contrato, seguridad y smoke
├── frontend/
│   ├── public/           # Manifest, service worker, offline e imágenes
│   └── src/
│       ├── app/          # Rutas App Router
│       ├── components/   # UI y componentes por dominio
│       ├── context/      # Contexto de ubicación
│       ├── hooks/        # Sesión, viajes, workflow, push y ubicación
│       ├── lib/          # Permisos, navegación, entorno y utilidades
│       ├── services/     # Cliente HTTP y servicios por módulo
│       ├── store/        # Estado de autenticación
│       └── types/        # Contratos TypeScript
├── infra/                # Compose, entorno y ejemplo NGINX
├── scripts/              # Arranque/parada/estado para Windows y shell
└── Docs/                 # Estado técnico y despliegue
```

---

# Principios Arquitectónicos

Esta sección distingue entre el uso observable de una tecnología y la motivación histórica. El repositorio confirma las decisiones implementadas, pero no contiene registros formales de arquitectura que demuestren por qué fueron elegidas originalmente. Las justificaciones siguientes son beneficios coherentes con la implementación actual, no citas de una decisión histórica.

| Decisión vigente | Función y beneficio observable | Grado de certeza |
|---|---|---|
| **FastAPI** | Expone una API REST tipada, integra dependencias de autenticación/DB y genera OpenAPI/Swagger. | Uso comprobado; motivación original no documentada. |
| **Next.js + React** | Organiza páginas con App Router, layouts protegidos, renderizado híbrido y componentes cliente para interacción/mapas. | Uso comprobado; motivación original no documentada. |
| **PostgreSQL** | Proporciona persistencia relacional para entidades conectadas, historial, catálogos y restricciones. | Uso comprobado; motivación original no documentada. |
| **Docker Compose** | Reproduce API y base de datos, separa ambientes de desarrollo/producción y controla exposición de puertos. | Uso y separación comprobados; motivación original no documentada. |
| **JWT Bearer** | Mantiene autenticación stateless entre frontend y API; `/auth/me` valida la sesión y el rol. | Uso comprobado; no se documenta comparación con sesiones de servidor. |
| **Cloudflare R2/S3** | Desacopla binarios de la base de datos mediante metadatos y URLs prefirmadas. | Integración parcial comprobada; razón de selección de R2 no documentada. |
| **Leaflet/React Leaflet** | Muestra ubicaciones operativas con librerías abiertas y componentes React. | Uso comprobado; criterio frente a otros proveedores no documentado. |
| **CRUD separado de routers** | Mantiene transporte HTTP separado de acceso a datos y reglas, facilitando reutilización y pruebas de contrato. | Separación comprobada; intención original no documentada. |
| **Bootstrap modular** | Centraliza fábrica, CORS, routers, esquema, seeds y startup. Permite componer el arranque sin sobrecargar `main.py`. | Uso y efecto comprobados. |
| **Pydantic** | Valida payloads y respuestas, expresa contratos y serializa entidades ORM. | Uso comprobado. |
| **SQLAlchemy** | Modela relaciones y consultas sin dispersar SQL por la capa HTTP. | Uso comprobado. |

## Principios de diseño derivados de la implementación

- La API es la autoridad de seguridad y reglas; los guards del frontend mejoran UX, pero no reemplazan autorización backend.
- Los routers traducen HTTP; la lógica de negocio pertenece a CRUD/helpers/servicios y no a componentes visuales.
- La disponibilidad se calcula desde fuentes operativas, evitando una bandera duplicada que pueda desincronizarse.
- Historiales, asignaciones y eventos preservan trazabilidad; no deben sobrescribirse como si fueran únicamente estado presente.
- Integraciones externas son configurables y deben degradarse de forma controlada cuando estén deshabilitadas.
- Los schemas y tipos forman contratos entre capas; un cambio requiere revisar productores y consumidores.

---

# Arquitectura Protegida

Los siguientes elementos se consideran **estables y protegidos**. No deben modificarse, renombrarse, eliminarse ni reorganizarse sin autorización expresa que identifique el elemento y acepte su impacto.

| Elemento protegido | Alcance de la protección |
|---|---|
| Arquitectura backend | Separación `api`/`crud`/`schemas`/`models`/`bootstrap`/`services`, fábrica de aplicación y dependencias. |
| Arquitectura frontend | App Router, grupos público/protegido, servicios, tipos, hooks, guards y componentes por dominio. |
| Organización de carpetas | Nombres, responsabilidades y rutas de importación existentes. |
| Contratos API | Métodos, rutas, parámetros, payloads, respuestas, códigos y semántica observable. |
| Modelos de datos | Tablas, columnas, claves, relaciones, constraints y significado de los datos. |
| Workflow de viajes | Estados, transiciones, requisitos, eventos, asignación y liberación de recursos. |
| Dashboard | Fuentes agregadas, KPIs, permisos, mapa, alertas y mantenimientos. |
| Autenticación | JWT, bootstrap administrativo, `/auth/me`, almacenamiento/consumo de sesión y control backend. |
| Roles y autorización | `ADMIN*`, `OPERADOR`, `MANTENIMIENTO` y pertenencia contextual de viajes. |
| Docker e infraestructura | Servicios, redes, puertos, volúmenes, variables y separación dev/prod. |

Una autorización para “mejorar” o “refactorizar” no implica automáticamente permiso para romper estos elementos. Antes de alterarlos se requiere: alcance explícito, análisis de compatibilidad, estrategia de datos/despliegue, validaciones aprobadas y revisión humana.

---

# Stack tecnológico

## Lenguajes

- Python (backend).
- TypeScript/TSX, JavaScript de configuración, HTML/CSS generado por React (frontend).
- SQL administrado mediante ORM.
- Shell y Batch para scripts locales.

No se encontró una versión de Python fijada explícitamente en el repositorio.

## Frameworks y librerías principales

- Backend: FastAPI, Uvicorn, SQLAlchemy, Pydantic, `pydantic-settings`, `psycopg`, `python-jose`, Passlib/bcrypt, boto3 y pywebpush.
- Frontend: Next.js 15.5.20, React 19, Tailwind CSS 3.4, Leaflet/React Leaflet y Lucide React.
- Base de datos: PostgreSQL 16.

## Herramientas de desarrollo

Docker/Docker Compose, npm, TypeScript 5.8, PostCSS, Autoprefixer, Pytest (en `requirements-dev.txt`) y scripts de administración local. No se detectaron ESLint/Prettier configurados de forma independiente, CI/CD versionado ni Alembic.

---

# Reglas de negocio

## Estados del viaje

| Estado | Significado | Terminal | Evidencia según catálogo |
|---|---|---:|---:|
| `CREADO` | Alta administrativa | No | No |
| `ASIGNADO` | Recursos asignados | No | No |
| `CARGANDO` | Carga previa al recorrido | No | No |
| `INICIADO` | Recorrido formal iniciado | No | Sí |
| `RETRASADO` | Viaje activo con retraso o percance | No | No |
| `STANDBY` | Pausa/resguardo sin cierre | No | No |
| `FINALIZADO` | Operación terminada | Sí | Sí |
| `CANCELADO` | Operación cancelada | Sí | No |

Las transiciones se almacenan en `transiciones_estatus_viaje`; algunas exigen comentario o evidencia. El seed vigente permite: `CREADO→ASIGNADO`, `ASIGNADO→CARGANDO`, `CARGANDO→INICIADO`, `INICIADO↔RETRASADO`, `INICIADO/RETRASADO→STANDBY`, `STANDBY→ASIGNADO/CARGANDO`, `INICIADO/RETRASADO→FINALIZADO` y cancelación desde `CREADO`, `ASIGNADO`, `CARGANDO` o `STANDBY`.

## Reglas operativas principales

- Un operador, tráiler o caja no puede asignarse simultáneamente a viajes activos incompatibles.
- La asignación crea historial y referencias a recursos actuales en el viaje.
- En `STANDBY` se liberan operador y tráiler; la caja permanece ligada.
- En `FINALIZADO` se liberan todos los recursos.
- La reasignación parte de `STANDBY` y controla recursos disponibles.
- El operador puede solicitar standby; administración autoriza la solicitud. Se impiden solicitudes pendientes duplicadas.
- Las acciones capturan eventos operativos: `INICIO_CARGA`, `INICIO_VIAJE`, `RETRASO`, `STANDBY` y `FINALIZACION_VIAJE` con ubicación y, según la acción, kilometraje, nivel de diésel y comentario.
- `iniciar-carga` exige ubicación; `marcar-retraso` exige ubicación y comentario. Otras acciones operativas validan su payload Pydantic.
- `INICIADO` solo puede alcanzarse mediante `POST /viajes/{id}/iniciar-viaje`. La acción exige en su payload al menos una evidencia nueva de tipo `EVIDENCIA_INICIO`; puede incluir `EVIDENCIA_GENERAL`, pero ésta no sustituye la evidencia obligatoria. `EVIDENCIA_CIERRE` y cualquier otro tipo no permitido se rechazan.
- `FINALIZADO` solo puede alcanzarse mediante `POST /viajes/{id}/finalizar`. La acción exige en su payload al menos una evidencia nueva de tipo `EVIDENCIA_CIERRE`; puede incluir `EVIDENCIA_GENERAL`, pero ésta no sustituye la evidencia obligatoria. `EVIDENCIA_INICIO` y cualquier otro tipo no permitido se rechazan.
- Las evidencias históricas no satisfacen una nueva acción de inicio o finalización. Las evidencias aceptadas se vinculan al evento operativo creado en la misma acción: `INICIO_VIAJE` o `FINALIZACION_VIAJE`.
- Inicio y finalización validan payload operativo, transición, asignación, evidencias y requisitos documentales antes de escribir. Ante cualquier excepción se ejecuta rollback para no persistir parcialmente evento, evidencias, historial, estatus, fechas, recursos o asignación.
- Con `STRICT_EVIDENCE_VALIDATION=true`, iniciar también requiere documentos vigentes del operador, tráiler y caja actual si existe; al finalizar se validan solo recursos todavía ligados.
- Operadores ven y operan únicamente viajes propios: por operador actual o asignación activa; ciertas operaciones terminales también admiten asignación histórica si no existe otro operador actual.
- Mantenimientos afectan la disponibilidad de tráilers/cajas. Las órdenes manejan checklist, archivos y evidencias, estados de ciclo y cierre/cancelación.
- La disponibilidad se deriva en consulta y considera actividad, viajes y mantenimientos.
- El bootstrap del primer administrador solo opera si está habilitado y se cierra cuando ya existe un usuario con rol administrativo.
- Usuarios inactivos no pueden autenticarse contra recursos protegidos.

## Roles y permisos

- `ADMIN` y variantes `ADMIN_*`: acceso administrativo; los catálogos y mutaciones críticas dependen de `require_admin`.
- `OPERADOR`: acceso contextual a viajes propios y experiencia de campo.
- `MANTENIMIENTO`: acceso al módulo de mantenimiento. Algunos endpoints admiten administración o mantenimiento, y otros admiten los tres perfiles.
- El frontend oculta navegación por rol, pero la autoridad definitiva está en dependencias del backend.

Las capacidades no están modeladas como permisos granulares por acción: se basan en nombres de rol y, para viajes, pertenencia contextual.

## Restricciones importantes

- JWT Bearer es obligatorio salvo health/login/bootstrap.
- Las eliminaciones de catálogos pueden quedar bloqueadas por referencias; la desactivación lógica se usa en varias entidades operativas.
- R2, Telegram y Web Push requieren configuración válida y banderas de activación.
- El frontend depende de `NEXT_PUBLIC_API_URL`; `/api` solo funciona si existe proxy/rewrite externo, que no se encontró en `next.config.mjs`.

---

# Módulos existentes

1. **Autenticación y sesión**: bootstrap del primer admin, login JWT y usuario actual.
2. **Roles y usuarios**: CRUD, activación y cambio de contraseña; vínculo opcional usuario-operador.
3. **Operadores, clientes, tráilers y cajas**: catálogos administrativos con CRUD y atributos logísticos/documentales.
4. **Viajes**: alta, edición, vistas enriquecidas, asignaciones, historial, mapa, transición y operación contextual.
5. **Workflow operativo**: carga, inicio, retraso, standby solicitado/directo, autorización, reinicio, reasignación, finalización y cancelación.
6. **Eventos operativos y KPIs**: snapshots de campo, edición administrativa, agregados por viaje, operador, tráiler y cliente.
7. **Evidencias y almacenamiento**: catálogo, asociación a viajes y URL prefirmada de R2.
8. **Documentos**: tipos y documentos asociados a viajes o entidades; consulta/gestión administrativa y validación de vigencia.
9. **Disponibilidad**: resumen y listados calculados de operadores, tráilers y cajas.
10. **Dashboard**: resumen administrativo agregado y tablero móvil del operador.
11. **Mapa de viajes**: última ubicación operativa conocida y filtros administrativos.
12. **Mantenimientos**: órdenes para recursos, checklist, archivos, evidencias y flujo de cierre/cancelación.
13. **Alertas**: generación, listado, lectura y procesamiento de notificaciones.
14. **Telegram**: destinatarios, pruebas y notificación de alertas.
15. **Web Push/PWA**: suscripción, baja, estado, pruebas, service worker, instalación y modo offline básico.
16. **Salud**: estado de API y ping de base de datos.

Los modelos `Incidencia` e `IncidenciaArchivo` existen en base de datos, pero no se encontró router, CRUD, schema ni página que los exponga; por tanto no constituyen un módulo funcional implementado.

---

# API

La API no usa un prefijo global versionado. Swagger queda disponible en `/docs` cuando la configuración estándar de FastAPI está activa.

## Salud y autenticación

- `GET /health`, `GET /db/ping`.
- `POST /auth/bootstrap-admin`, `POST /auth/login`, `GET /auth/me`.

## Catálogos administrativos

- `/roles`, `/usuarios`, `/operadores`, `/clientes`, `/trailers`, `/cajas`: `POST`, `GET` listado, `GET /{id}`, `PUT /{id}` y `DELETE /{id}`.
- Usuarios añade `PATCH /usuarios/{id}/password`.

## Viajes y consulta

- `POST/GET /viajes/`, `PUT/GET /viajes/{id}`.
- `GET /viajes/enriched`, `/viajes/mapa`, `/viajes/{id}/detail`.
- Catálogos: `GET /viajes/catalogos/tipos-evidencia`, `/tipos-documento` y `/archivos-prueba`.
- Historial/asignaciones: `GET /viajes/{id}/historial-estatus[/enriched]`, `POST/GET /viajes/{id}/asignaciones`, `GET .../asignaciones/enriched`.

## Workflow y disponibilidad

- `POST /viajes/{id}/asignar`, `/iniciar-carga`, `/iniciar-viaje`, `/marcar-retraso`, `/poner-standby`, `/solicitar-standby`, `/autorizar-standby`, `/reiniciar-viaje`, `/reasignar`, `/finalizar`, `/cancelar` y `/cambiar-estatus`.
- `POST /viajes/{id}/cambiar-estatus` rechaza con HTTP 400 los destinos `INICIADO` y `FINALIZADO`, indicando respectivamente `/iniciar-viaje` y `/finalizar`; los destinos inexistentes y las demás transiciones conservan su flujo de validación anterior.
- `GET /viajes/{id}/transiciones-disponibles`.
- `GET /viajes/disponibilidad/resumen`, `/operadores`, `/trailers`, `/cajas`.

## Eventos, evidencias y documentos

- `GET /viajes/{id}/eventos-operativos`; `PUT /viajes/{id}/eventos-operativos/{evento_id}`.
- CRUD anidado de `/viajes/{id}/evidencias`; `POST /evidencias/presign-upload`.
- Documentos anidados en viaje y en `operador-actual`, `trailer-actual`, `caja-actual`.
- Administración: `GET /documentos/tipos`, `GET/POST /documentos`, `PUT/DELETE /documentos/{id}`.

## KPIs y dashboard

- `GET /dashboard/admin`.
- `GET /viajes/kpis-operativos` con filtros temporales y por entidades/estatus.
- `GET /kpis/operadores`, `/kpis/trailers`, `/kpis/clientes`.

## Mantenimientos

- `GET/POST /mantenimientos`, `GET/PUT /mantenimientos/{id}`.
- `GET /mantenimientos/recursos-disponibles`.
- `POST /mantenimientos/{id}/cerrar` y `/cancelar`.
- Actualización de checklist; CRUD de archivos; CRUD de evidencias por elemento de checklist.

## Alertas y notificaciones

- `GET /alertas`, `PATCH /alertas/{id}/leer`, `POST /alertas/generar`, `POST /alertas/notificar-pendientes`.
- CRUD de `/telegram/destinatarios` y `POST /telegram/test/{id}`.
- `POST /push/subscribe`, `DELETE /push/unsubscribe`, `GET /push/status`, `POST /push/test` y `POST /push/test/{id_usuario}`.

Los parámetros, payloads y códigos exactos deben consultarse en schemas y OpenAPI; este resumen evita presentar como universales dependencias de rol que varían por endpoint.

---

# Dashboard

## Arquitectura actual

`/dashboard` selecciona la experiencia según el rol. Administración consume un agregado único de `GET /dashboard/admin`; el operador usa su listado contextual de viajes. `/dashboard/kpis` ofrece análisis operacional con filtros. Los componentes están en `src/components/dashboard` y `src/components/kpis`.

## Componentes

- `AdminDashboard`, `OperatorDashboard`.
- `DashboardKpiGrid`, `DashboardStatusOverview`, `DashboardAvailabilityPanel`.
- `DashboardAlertList`, `DashboardMaintenanceList`, `DashboardSectionCard`, `StatCard`.
- Componentes KPI: resumen, filtros, tabla por viaje, estados y vacío.

## KPIs

El tablero administrativo resume viajes totales/activos/standby/por estado; disponibilidad de operadores, tráilers y cajas; alertas; mantenimientos; cobertura de ubicación; viajes con eventos; kilómetros promedio; consumo estimado de diésel y viajes finalizados con KPI. El tablero analítico permite filtrar por fecha, operador, tráiler, cliente y estado según el endpoint consumido, y muestra integridad/anomalías por viaje.

## Mapa

Usa Leaflet y la última latitud/longitud disponible en eventos operativos. El dashboard muestra un mapa compacto; `/admin/mapa-viajes` ofrece la vista completa y filtros. Se contabilizan viajes con y sin ubicación. No es rastreo GPS continuo: son snapshots capturados durante acciones.

## Alertas

Muestra pendientes, críticas no leídas e ítems priorizados. La administración puede generar alertas, marcarlas como leídas y disparar procesamiento de notificaciones.

## Mantenimientos

Resume órdenes abiertas, en proceso y próximas, con elementos vinculados a tráileres o cajas. La operación detallada vive en páginas administrativas y del perfil de mantenimiento.

---

# Frontend

## Organización

- `app/(public)/login`: acceso público.
- `app/(protected)`: shell autenticado; dashboard, viajes, mantenimiento y administración.
- `components`: agrupados por `admin`, `auth`, `dashboard`, `kpis`, `layout`, `location`, `pwa`, `ui` y `viajes`.
- `services`: funciones por recurso sobre `api-client.ts`.
- `hooks`: orquestación de sesión, viajes, detalle, workflow, ubicación persistente y push.
- `types`: contratos por dominio; duplican deliberadamente contratos de respuesta del backend.

## Componentes importantes

`AppShell`, sidebar/topbar/navegación móvil; `SessionGuard`, `AdminGuard`, `MaintenanceGuard`; tablas y cards de viajes; detalle del operador y panel de acciones; timeline, resumen, asignaciones, evidencias y mapas; dashboards; tablas/modales administrativos; banners y configuración PWA.

## Servicios

Hay servicios para auth, usuarios, roles, operadores, clientes, tráilers, cajas, viajes/workflow, evidencias, documentos, dashboard/KPIs, mantenimientos, alertas, Telegram y Push. `api-client.ts` centraliza URL base, token y manejo HTTP.

## Tipos

Los tipos se separan por dominio (`viaje`, `dashboard`, `mantenimiento`, `alerta`, etc.). No se encontró generación automática desde OpenAPI, por lo que backend y frontend deben mantenerse sincronizados manualmente.

## Páginas

- Públicas: `/login`.
- Comunes/protegidas: `/dashboard`, `/dashboard/kpis`, `/viajes`, `/viajes/[viajeId]`.
- Administración: inicio, alta/edición de viajes, mapa, disponibilidad, alertas, mantenimientos, Telegram y CRUDs de catálogos/documentos.
- Mantenimiento: listado, alta y detalle.
- `/admin/evidencias` y `/admin/perfil` muestran placeholders; `/admin/documentos` sí contiene una implementación de consulta/gestión.

---

# Backend

## Organización

`main.py` expone la instancia construida por `create_app()`. `bootstrap/` compone la aplicación; `api/` traduce HTTP; `crud/` concentra consultas y reglas; `schemas/` valida entrada/salida; `models/models.py` define el ORM; `core/` maneja configuración, JWT y R2; `services/` integra notificaciones.

## Routers

Los routers se registran explícitamente en `bootstrap/routers.py`. Están separados por auth, salud, viajes, evidencias, documentos, dashboard, alertas, KPIs, mantenimientos, push, Telegram y cada catálogo maestro.

## CRUD

Existen módulos CRUD por catálogo y por dominio. `crud_viajes.py` concentra el workflow y es el archivo de lógica más amplio; `viajes_helpers.py` agrupa consultas auxiliares. Dashboard/KPIs, mantenimientos, alertas, Telegram y usuarios tienen módulos dedicados. En inicio y finalización, `crud_viajes.py` prevalida la acción antes de crear eventos o evidencias, mantiene `cambiar_estatus_viaje` como propietario del commit exitoso y ejecuta rollback ante cualquier excepción.

## Schemas

Pydantic separa modelos `Create`, `Update`, `Response`, payloads operativos, vistas enriquecidas y agregados. Se usa `from_attributes` donde corresponde para serializar ORM.

## Modelos

Los modelos se concentran en un único `models.py`: roles/usuarios; recursos y clientes; viajes, estatus, transiciones, asignaciones, historial y eventos; almacenamiento/documentos/evidencias; mantenimiento/checklist/archivos; alertas/destinatarios/suscripciones; incidencias aún no expuestas.

## Bootstrap

En startup se prepara el esquema y se ejecutan seeds de roles, estados/transiciones, evidencias y documentos. `schema_bootstrap.py` crea tablas y aplica ajustes incrementales mediante SQL/inspección. CORS se configura por entorno. Este mecanismo sustituye actualmente a migraciones versionadas.

---

# Base de datos

## Modelo general y entidades

- **Identidad**: `roles` 1:N `usuarios`; un usuario puede vincularse con un operador.
- **Recursos**: `operadores`, `trailers`, `cajas`; **cliente**: `clientes`.
- **Operación**: `viajes` referencia cliente, estado actual y recursos actuales. `asignaciones_viaje` conserva asignaciones; `historial_estatus_viaje` conserva cambios; `eventos_operativos_viaje` captura snapshots.
- **Workflow configurable**: `catalogo_estatus_viaje` y `transiciones_estatus_viaje`.
- **Archivos**: `archivos_storage` representa objetos; `documentos` asocia archivo/tipo a distintas entidades; `evidencias` asocia tipo y archivo a viajes.
- **Mantenimiento**: orden principal, checklist, evidencias por rubro y archivos generales.
- **Alertamiento**: `alertas`, destinatarios de Telegram y suscripciones push.
- **Incidencias**: tablas de incidencia y archivos existen sin capa funcional expuesta.

## Relaciones relevantes

Un cliente tiene muchos viajes. Un viaje tiene muchas asignaciones, cambios de estado, eventos, evidencias y documentos, y referencias opcionales a operador/tráiler/caja actuales. Los recursos pueden participar históricamente en muchas asignaciones. Documentos usan una asociación polimórfica por tipo/id de entidad además del registro de archivo. Mantenimientos apuntan a un tipo de recurso y conservan sus colecciones auxiliares.

No se encontró diagrama ER ni migraciones Alembic que documenten constraints a través del tiempo; `models.py` y `schema_bootstrap.py` son las fuentes vigentes.

---

# Docker

## Desarrollo recomendado

1. Crear `infra/.env` a partir de `infra/.env.example` y usar valores locales seguros.
2. Levantar API y DB:

   ```powershell
   docker compose -f infra/compose.dev.yml --env-file infra/.env up --build
   ```

3. En otra terminal, preparar `frontend/.env.local` y levantar frontend:

   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

Accesos locales documentados: frontend `http://localhost:3000`, API `http://localhost:8080`, Swagger `http://localhost:8080/docs` y PostgreSQL `localhost:5432` solo con Compose de desarrollo.

## Producción/base

```powershell
docker compose -f infra/compose.prod.yml --env-file infra/.env up --build -d
```

`compose.yml` ofrece una variante base con bind mount; `compose.prod.yml` evita ese mount. Ningún Compose levanta el frontend ni NGINX.

## Variables importantes

- DB: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`.
- Seguridad: `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `BOOTSTRAP_ADMIN_ENABLED`, `CORS_ALLOWED_ORIGINS`.
- Reglas: `STRICT_EVIDENCE_VALIDATION`.
- R2: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_ENDPOINT_URL`, `R2_PUBLIC_BASE_URL`.
- Telegram: `TELEGRAM_ENABLED`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_DEFAULT_CHAT_ID`, `APP_PUBLIC_URL`.
- Push: `WEB_PUSH_ENABLED`, claves VAPID y `WEB_PUSH_SUBJECT`.
- Frontend: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WEB_PUSH_PUBLIC_KEY`.

Dentro de Docker, `DATABASE_URL` debe apuntar a `db:5432`, no a `localhost`. No deben copiarse secretos reales a archivos versionados.

---

# Convenciones

- Backend en `snake_case`; clases Python/Pydantic/ORM en `PascalCase`; constantes en mayúsculas.
- Frontend: componentes y tipos en `PascalCase`, funciones/variables en `camelCase`, archivos y rutas en `kebab-case` o nombres de dominio en minúsculas.
- Claves de estados y roles en mayúsculas; nombres HTTP y tablas principalmente en español.
- Separación router → CRUD → ORM, con schemas Pydantic en la frontera HTTP.
- Servicios frontend por dominio y un cliente HTTP común; alias `@/` para `src`.
- Componentes cliente marcados con `"use client"`; mapas se aíslan para evitar renderizado en servidor de APIs del navegador.
- Acceso condicionado tanto en frontend (guards/navegación) como backend (dependencias).
- Respuestas enriquecidas evitan que la UI reconstruya relaciones desde IDs.
- Seeds idempotentes por existencia y configuración central por variables de entorno.
- Recursos visuales reutilizables se concentran en `components/ui`.

---

# Buenas Prácticas

## Generales

- Leer este documento y el código afectado antes de proponer una solución.
- Confirmar el alcance y distinguir hechos comprobados de inferencias.
- Mantener cada cambio enfocado; evitar refactors incidentales.
- Reutilizar componentes, servicios, schemas, helpers y patrones existentes antes de crear otros.
- Preservar compatibilidad hacia atrás y documentar cualquier impacto previsto.
- Mantener nombres de dominio en español y convenciones técnicas vigentes.
- Explicar decisiones no obvias cerca de la lógica cuando un comentario aporte contexto, no cuando repita el código.
- No introducir secretos, credenciales ni datos personales en el repositorio, logs o respuestas.

## Backend

- Mantener validación HTTP en schemas/dependencias y reglas de dominio en CRUD/helpers/servicios.
- Aplicar autorización en el backend aunque el frontend oculte la acción.
- Usar transacciones coherentes al modificar viaje, historial, asignaciones y recursos relacionados.
- Conservar trazabilidad; crear eventos/historial cuando corresponda en vez de sobrescribir evidencia histórica.
- Evitar consultas N+1 y usar respuestas enriquecidas existentes cuando el consumidor necesita relaciones.
- Tratar cambios de modelo o esquema como cambios protegidos que requieren autorización y estrategia explícita.

## Frontend

- Consumir la API mediante `services/` y `api-client.ts`; no dispersar `fetch` ni manejo de token.
- Reutilizar contratos de `types/`, hooks y componentes UI existentes.
- Mantener estados de carga, error y vacío, además de accesibilidad y diseño responsive.
- Conservar la experiencia móvil del operador y la separación de navegación por rol.
- Aislar en componentes cliente cualquier dependencia de navegador, geolocalización o Leaflet.

## Validación y entrega

- Ejecutar únicamente validaciones autorizadas y reportar con precisión qué se ejecutó y qué no.
- Revisar el diff y el estado del repositorio para detectar archivos inesperados.
- Actualizar esta Constitución cuando un cambio aprobado altere información que contiene.
- Entregar un resumen, impacto, validación y pendientes sin afirmar resultados no comprobados.

---

# Errores que Deben Evitarse

1. Modificar contratos, endpoints, tablas, columnas o estados para simplificar una implementación local.
2. Duplicar componentes, servicios, tipos, consultas o reglas sin revisar primero lo existente.
3. Crear nuevos servicios o capas cuando un módulo vigente ya tiene esa responsabilidad.
4. Mover reglas críticas al frontend o confiar en guards visuales como autorización.
5. Cambiar nombres públicos, formatos o semántica sin plan de compatibilidad aprobado.
6. Modificar modelos o bootstrap de esquema como efecto secundario de otra tarea.
7. Reinterpretar reglas de negocio a partir del nombre de una función; se deben confirmar en flujo, CRUD, seeds y contratos.
8. Mezclar refactors, formato general y cambios funcionales en la misma intervención.
9. Eliminar funcionalidad, historial o validaciones porque parezcan no utilizadas.
10. Exponer PostgreSQL, API, secretos o integraciones de producción innecesariamente.
11. Ejecutar pruebas, migraciones, instalaciones, commits, push o despliegues sin autorización.
12. Ocultar fallos de validación, ampliar silenciosamente el alcance o declarar éxito sin evidencia.

---

# Riesgos técnicos

1. **Sin migraciones versionadas**: cambios incrementales en startup son difíciles de auditar, revertir y reproducir entre ambientes.
2. **Modelo ORM monolítico**: `models.py` concentra todas las entidades y aumentará el acoplamiento al crecer.
3. **Workflow centralizado y extenso**: `crud_viajes.py` reúne muchas reglas críticas y eleva el costo de cambio/regresión.
4. **Contratos duplicados manualmente**: tipos TypeScript y schemas Pydantic pueden divergir.
5. **Autorización por nombre de rol**: prefijo `ADMIN_` y comparaciones de strings no ofrecen permisos granulares ni un catálogo formal de capacidades.
6. **Integridad de asociaciones polimórficas**: documentos/mantenimientos basados en tipo + ID tienen menos garantías de FK que relaciones dedicadas.
7. **Estado derivado complejo**: disponibilidad depende de coherencia entre referencias actuales, asignaciones, estados y mantenimientos.
8. **Ubicación no continua**: el mapa refleja eventos puntuales, no telemetría en tiempo real; puede parecer desactualizado.
9. **Frontend fuera de Compose**: el despliegue completo requiere coordinación externa con PM2/NGINX no codificada en Compose.
10. **Configuración sensible**: JWT, R2, Telegram y VAPID dependen de secretos externos; valores faltantes deshabilitan o rompen capacidades asociadas.
11. **Sin CI/CD visible**: no se encontró automatización versionada que valide pruebas, tipos, lint o despliegues.
12. **Dependencias backend no fijadas**: salvo bcrypt, `requirements.txt` no define versiones; builds futuros pueden variar.
13. **Persistencia JWT en navegador**: el almacenamiento accesible desde JavaScript incrementa el impacto potencial de XSS.
14. **Datos seed de prueba**: `/viajes/archivos-prueba` y seeds auxiliares deben revisarse para evitar exposición o uso accidental en producción.

---

# Pendientes técnicos

## Detectados explícitamente

- Completar la integración real de almacenamiento R2; actualmente hay soporte prefirmado y datos de prueba, pero la documentación reconoce integración parcial.
- Filtros avanzados mencionados como pendientes en `README.md`; algunas vistas ya tienen filtros, por lo que el alcance exacto restante no está definido.
- `/admin/evidencias` continúa como placeholder.
- `/admin/perfil` continúa como placeholder.

## Inferidos del estado del código

- Implementar capa funcional para `Incidencia` e `IncidenciaArchivo`, o retirar/documentar esos modelos si no forman parte del alcance.
- Sustituir `schema_bootstrap.py` por migraciones versionadas o definir formalmente cómo se controla la evolución del esquema.
- Añadir generación/validación automática de contratos frontend desde OpenAPI.
- Incorporar frontend y proxy a una definición reproducible de despliegue, si ése es el modelo operativo deseado.
- Aclarar si `/api` en `frontend/.env.example` depende de NGINX externo; no existe rewrite local en Next.js.
- Consolidar documentación antigua: algunos pendientes del README ya fueron implementados (por ejemplo, vistas enriquecidas y documentos), por lo que no debe asumirse que todas sus listas siguen vigentes.

No se encontraron marcadores literales `TODO`, `FIXME` o `HACK` relevantes en código fuente. No se infiere fecha, responsable ni prioridad para los pendientes.

---

# Cómo Trabajar en este Proyecto

Toda tarea debe seguir el procedimiento siguiente. Omitir una fase requiere autorización explícita; la urgencia no elimina controles de seguridad o alcance.

| Fase | Acción obligatoria | Resultado esperado |
|---:|---|---|
| 1 | **Analizar** | Leer la solicitud, esta Constitución y el estado relevante del repositorio. |
| 2 | **Entender el problema** | Definir comportamiento actual, resultado esperado, restricciones y dudas. |
| 3 | **Localizar archivos** | Identificar productores, consumidores, contratos y validaciones implicados. |
| 4 | **Proponer solución** | Explicar enfoque, impacto, riesgos y archivos previstos sin cambiar código. |
| 5 | **Esperar aprobación** | Obtener autorización humana del enfoque y alcance. |
| 6 | **Modificar únicamente archivos autorizados** | Implementar el cambio mínimo, sin ediciones incidentales. |
| 7 | **Explicar cambios** | Describir qué cambió, por qué y cuál es su impacto. |
| 8 | **Ejecutar únicamente validaciones autorizadas** | Correr solo checks aprobados y reportar resultados reales. |
| 9 | **Esperar revisión humana** | Entregar el trabajo sin asumir aceptación. |
| 10 | **Commit manual** | Una persona revisa y crea el commit; la IA no lo hace automáticamente. |
| 11 | **Push manual** | Una persona decide y ejecuta el push; la IA no lo hace automáticamente. |

Si la tarea autoriza directamente una implementación concreta, esa autorización cubre la propuesta descrita en la solicitud, pero no concede permiso implícito para ampliar el alcance ni alterar [Arquitectura Protegida](#arquitectura-protegida).

---

# Reglas para IA

Estas reglas son obligatorias para cualquier IA que trabaje en el proyecto:

## Prohibiciones

- Nunca hacer commit automáticamente.
- Nunca hacer push automáticamente.
- Nunca modificar archivos fuera de los solicitados o autorizados.
- Nunca cambiar arquitectura sin autorización expresa.
- Nunca eliminar funcionalidades, controles o datos existentes sin autorización expresa.
- Nunca cambiar contratos públicos, nombres de endpoints, tablas, columnas, estados o roles sin autorización expresa.
- Nunca modificar modelos, relaciones, constraints, seeds o bootstrap de esquema sin autorización expresa.
- Nunca asumir reglas de negocio ni completar vacíos con información inventada.
- Nunca ejecutar pruebas, migraciones, instalaciones, despliegues o acciones destructivas que no estén autorizadas.
- Nunca sobrescribir cambios ajenos ni limpiar un worktree sucio para facilitar la tarea.

## Obligaciones

- Leer `AI_CONTEXT.md` antes de trabajar y contrastar su información con el código relevante.
- Justificar cada cambio y explicar su impacto funcional, técnico y de compatibilidad.
- Respetar backward compatibility salvo autorización explícita en sentido contrario.
- Aplicar el cambio mínimo y respetar los patrones existentes.
- Informar incertidumbres, discrepancias y riesgos antes de decidir.
- Revisar que no haya archivos inesperados al terminar.
- Indicar con exactitud las validaciones ejecutadas y las omitidas.
- Señalar si el cambio aprobado requiere actualizar esta Constitución.

---

# Flujo Oficial ChatGPT + Codex

```text
ChatGPT
   ↓
Define estrategia
   ↓
Genera instrucciones específicas
   ↓
Codex implementa únicamente el alcance autorizado
   ↓
Codex explica cambios, impacto y validación
   ↓
Humano revisa
   ↓
ChatGPT valida estrategia y resultado
   ↓
Commit manual
   ↓
Push manual
```

## Responsabilidades

| Participante | Responsabilidad |
|---|---|
| **ChatGPT** | Dirigir estrategia, prioridades, decisiones y criterios de aceptación. |
| **Codex** | Analizar el repositorio y ejecutar tareas específicas dentro del alcance autorizado. |
| **Humano** | Autorizar, revisar, aceptar o rechazar; controlar commit, push y despliegue. |

Codex no sustituye la decisión estratégica de ChatGPT ni la aprobación humana. ChatGPT no convierte una propuesta en cambio aceptado sin revisión humana.

---

# Checklist Antes de Modificar Código

Debe completarse mentalmente o registrarse en la tarea antes de editar:

- [ ] Comprendí el problema, el resultado esperado y las restricciones.
- [ ] Revisé `AI_CONTEXT.md` y el código relevante.
- [ ] Identifiqué todos los archivos, contratos y consumidores afectados.
- [ ] Distinguí hechos comprobados de supuestos y resolví dudas materiales.
- [ ] Propuse la solución y existe aprobación para implementarla.
- [ ] Modificaré únicamente archivos autorizados.
- [ ] No romperé contratos, API, frontend, datos ni compatibilidad.
- [ ] No cambiaré arquitectura, modelos ni reglas de negocio sin autorización.
- [ ] No eliminaré funcionalidad existente.
- [ ] No haré commit ni push.
- [ ] Sé qué validaciones están autorizadas.
- [ ] Documentaré cambios, impacto y riesgos.

---

# Checklist Antes de Terminar una Tarea

La casilla de compilación/pruebas solo puede marcarse cuando esa validación fue autorizada y realmente ejecutada; de lo contrario debe reportarse como “no ejecutada”.

- [ ] La implementación coincide con el alcance aprobado.
- [ ] El código compiló o se reportó explícitamente que no se autorizó/no se ejecutó la compilación.
- [ ] Las validaciones autorizadas finalizaron y se reportaron sus resultados.
- [ ] No hay archivos modificados o generados inesperadamente.
- [ ] No hubo cambios fuera del alcance.
- [ ] Se respetaron arquitectura, contratos y compatibilidad.
- [ ] Se explicaron cambios, impacto, riesgos y pendientes.
- [ ] Se indicó si `AI_CONTEXT.md` necesita actualización.
- [ ] No se hizo commit.
- [ ] No se hizo push.
- [ ] El resultado queda pendiente de revisión humana.

---

# Roadmap

No se encontró un roadmap formal ni datos suficientes para inventar sprints, fechas, responsables o estados. Las entradas deben agregarse únicamente cuando hayan sido definidas y aprobadas.

## Plantilla de sprint

| Campo | Contenido |
|---|---|
| **Sprint** | Identificador o nombre aprobado |
| **Objetivo** | Resultado de negocio/técnico esperado |
| **Estado** | Planeado / En curso / Bloqueado / Completado / Cancelado |
| **Fecha** | Inicio y fin, si están definidos |
| **Responsable** | Persona/equipo asignado |
| **Observaciones** | Dependencias, riesgos, criterios de aceptación y enlaces |

```markdown
## Sprint [identificador] — [nombre]

- **Objetivo:**
- **Estado:**
- **Fecha:**
- **Responsable:**
- **Alcance:**
- **Criterios de aceptación:**
- **Dependencias/riesgos:**
- **Observaciones:**
```

---

# Changelog IA

Registra cada intervención futura que produzca cambios materiales. No sustituye al historial de Git ni debe incluir secretos, razonamiento privado o afirmaciones no verificadas.

## Plantilla

```markdown
## AAAA-MM-DD — [objetivo breve]

- **IA/herramienta:**
- **Objetivo:**
- **Archivos modificados:**
- **Motivo:**
- **Cambios:**
- **Impacto/compatibilidad:**
- **Validación autorizada y resultado:**
- **Validaciones no ejecutadas:**
- **Pendientes:**
- **Revisión humana:** Pendiente / Aprobada / Rechazada
```

## 2026-08-05 — Evidencias específicas de inicio y cierre

- **IA/herramienta:** Codex.
- **Objetivo:** diferenciar las evidencias nuevas exigidas al iniciar y finalizar un viaje y bloquear esas transiciones desde el endpoint genérico.
- **Archivos modificados:** `backend/app/api/routes_viajes.py`, `backend/app/crud/crud_viajes.py`, `backend/tests/test_dashboard_admin_contract.py`, `backend/tests/test_viajes_contract.py` y `backend/tests/test_viaje_evidencias_workflow_persistence.py`.
- **Motivo:** impedir que evidencias generales, históricas o correspondientes a la etapa contraria satisfagan las transiciones a `INICIADO` o `FINALIZADO`.
- **Cambios:** validación de `EVIDENCIA_INICIO` y `EVIDENCIA_CIERRE` por acción; `EVIDENCIA_GENERAL` como complemento; rechazo de tipos prohibidos o no permitidos; prevalidación y rollback atómico; bloqueo HTTP 400 del endpoint genérico; pruebas persistentes y contractuales. También se corrigió el aislamiento de una prueba del dashboard para evitar ejecutar accidentalmente el startup real.
- **Impacto/compatibilidad:** sin cambios de modelos, schemas, seeds, migraciones ni contratos JSON. Las demás transiciones genéricas conservan su comportamiento.
- **Validación autorizada y resultado:** 33 pruebas de workflow y persistencia aprobadas; 9 pruebas contractuales de viajes aprobadas; prueba de zona horaria del dashboard aprobada; suite backend completa con 128 pruebas aprobadas, 0 fallidas y 0 errores.
- **Validaciones no ejecutadas:** pruebas del frontend.
- **Pendientes:** push pendiente de autorización.
- **Revisión humana:** Aprobada.
- **Commit funcional:** `baf5a31 feat(viajes): validar evidencias de inicio y cierre`.

## 2026-08-03 — Conversión a Constitución Técnica

- **IA/herramienta:** Codex.
- **Objetivo:** convertir `AI_CONTEXT.md` en documento maestro y memoria técnica permanente.
- **Archivos modificados:** `AI_CONTEXT.md`.
- **Motivo:** establecer principios, arquitectura protegida, flujo obligatorio, reglas para IA, checklists y plantillas de gobierno.
- **Cambios:** reorganización navegable y ampliación normativa, conservando el contexto técnico existente.
- **Impacto/compatibilidad:** solo documentación; sin cambios de código, API, datos o infraestructura.
- **Validación autorizada y resultado:** revisión estática del archivo y del alcance documental.
- **Validaciones no ejecutadas:** pruebas y compilaciones, por instrucción expresa.
- **Pendientes:** revisión humana.
- **Revisión humana:** Pendiente.

---

# Lecciones Aprendidas

Esta sección debe registrar aprendizajes confirmados que cambien cómo se diseña, implementa, valida u opera el sistema. No debe usarse para opiniones sin evidencia.

## Plantilla

```markdown
## AAAA-MM-DD — [decisión o aprendizaje]

- **Contexto:**
- **Problema observado:**
- **Decisión tomada:**
- **Resultado/evidencia:**
- **Principio aplicable a futuro:**
- **Alternativas descartadas y motivo:**
- **Áreas afectadas:**
- **Revisión futura:**
```

No hay entradas históricas suficientemente documentadas para completar esta sección sin inventar información.

---

# Historial técnico

Esta sección está preparada para registrar cambios importantes. Cada entrada futura debe describir hechos verificables y enlazar, cuando aplique, la tarea o decisión que los autorizó.

## Formato de entrada

```markdown
## AAAA-MM-DD — Título breve

- **Objetivo:** problema o necesidad atendida.
- **Alcance:** módulos y archivos relevantes.
- **Decisiones:** decisiones arquitectónicas o de negocio.
- **Cambios:** resumen técnico verificable.
- **Base de datos/API:** migraciones y contratos afectados, o “Sin cambios”.
- **Validación:** comprobaciones realizadas y resultado.
- **Riesgos/pendientes:** seguimiento necesario.
```

## 2026-08-03 — Creación del contexto técnico para IA

- **Objetivo:** consolidar el estado observable del repositorio para futuras instancias de Codex.
- **Alcance:** análisis de backend, frontend, infraestructura, documentación y scripts; creación exclusiva de `AI_CONTEXT.md`.
- **Decisiones:** documentar como hechos solo elementos confirmados en el repositorio y señalar de forma explícita las inferencias o ausencias.
- **Cambios:** se agregó este documento; no se modificó código existente.
- **Base de datos/API:** sin cambios.
- **Validación:** revisión estática del repositorio; no se ejecutaron pruebas por instrucción expresa.
- **Riesgos/pendientes:** mantener este archivo sincronizado después de cambios arquitectónicos, de negocio, API, datos o despliegue.
