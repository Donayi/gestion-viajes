# 📊 Estado Actual del Proyecto (Generado con ChatGPT)

## 🧠 Contexto General

Este proyecto fue diseñado iterativamente con enfoque en:

* Correcta modelación de negocio
* Separación de responsabilidades
* Escalabilidad del flujo de viajes

---

## 🏗️ Estado actual del backend

### CRUD completos

* Roles
* Usuarios
* Operadores
* Clientes
* Tráileres
* Cajas

### Seguridad mínima implementada

* Bootstrap inicial de administrador con `POST /auth/bootstrap-admin`
* Login JWT con Bearer token
* `GET /auth/me` para validar sesión
* Autorización por roles:
  * `ADMIN`
  * `OPERADOR`
* Restricción contextual de viajes para operadores

### Frontend base implementado

* `frontend/` con `Next.js + TypeScript + TailwindCSS`
* Login conectado a `POST /auth/login`
* Sesión validada con `GET /auth/me`
* Layout protegido en:
  * `/dashboard`
  * `/viajes`
* Dashboard básico con métricas simples
* Lista de viajes enriquecidos
* Detalle de viaje con historial y asignaciones enriquecidas
* Acciones básicas de workflow desde UI
* Subida real de evidencias desde frontend usando presigned URLs hacia Cloudflare R2

---

## 🚛 Módulo de viajes (núcleo del sistema)

### Tablas principales

* viajes
* asignaciones_viaje
* historial_estatus_viaje
* catalogo_estatus_viaje
* transiciones_estatus_viaje

---

## 🔄 Workflow implementado

### Estados

* CREADO
* ASIGNADO
* CARGANDO
* INICIADO
* RETRASADO
* STANDBY
* FINALIZADO
* CANCELADO

---

## 🔁 Transiciones controladas

No se permiten cambios arbitrarios.

Todo cambio pasa por:

```
transiciones_estatus_viaje
```

---

## ⚙️ Lógica implementada

### Asignación

* valida disponibilidad
* cierra asignación anterior
* crea nueva asignación
* actualiza viaje

### Cambio de estatus

* valida transición
* valida reglas de negocio
* actualiza viaje
* registra historial

---

## 📦 Disponibilidad de recursos

### Operadores

No disponibles si:

* tienen asignación activa

### Tráileres

No disponibles si:

* tienen asignación activa

### Cajas

No disponibles si:

* están en asignación activa
* están en viaje no finalizado

---

## 🔥 Comportamientos clave

### STANDBY

* libera operador
* libera tráiler
* mantiene caja

### FINALIZADO

* libera todo
* cierra asignación
* marca fecha fin

---

## 🧪 Endpoints funcionales

### Disponibilidad

* `/viajes/disponibilidad/*`

### Workflow

* `/viajes/{id}/asignar`
* `/viajes/{id}/iniciar-carga`
* `/viajes/{id}/iniciar-viaje`
* `/viajes/{id}/poner-standby`
* `/viajes/{id}/reasignar`
* `/viajes/{id}/finalizar`
* `/viajes/{id}/cancelar`
* `/viajes/{id}/eventos-operativos`
* `/viajes/kpis-operativos`

---

## ❗ Decisiones importantes de arquitectura

### 1. NO usar tablas de disponibilidad

✔ Se calcula en tiempo real
✔ Evita inconsistencias

---

### 2. Uso de historial de estatus

✔ Auditoría completa
✔ Trazabilidad

---

### 3. Uso de asignaciones versionadas

✔ Permite cambios de operador/tráiler
✔ Soporta standby y reasignación

---

### 4. Autorización contextual reutilizable

✔ La autenticación vive fuera del workflow
✔ La pertenencia de viajes para operadores se resuelve desde `crud_viajes.py`
✔ Las rutas solo aplican dependencias y validaciones de acceso

---

## 🚧 Pendientes prioritarios

### 1. Validación de evidencias

Antes de permitir:

* INICIADO
* FINALIZADO

Debe existir:

* evidencia cargada
* base preparada para validación documental más estricta

### Estado implementado

La validación ya quedó centralizada en:

```
cambiar_estatus_viaje()
```

Reglas activas:

* Se dispara únicamente cuando `transicion.requiere_evidencia = true`
* Para `INICIADO` exige al menos una evidencia asociada al viaje con `id_archivo` válido
* Para `FINALIZADO` exige al menos una evidencia asociada al viaje
* El código quedó preparado para diferenciar evidencia de cierre más adelante

Compatibilidad:

* Se agregó `strict_evidence_validation = false` en configuración
* Si se activa en `true`, se ejecuta validación documental estricta desde `crud_viajes.py`
* Si se mantiene en `false`, el flujo actual no se rompe
* Ya existe un CRUD base de evidencias anidado bajo viajes para desbloquear pruebas operativas
* Ya existe un CRUD mínimo de documentos asociado al viaje y a recursos actuales para probar validación estricta
* Se sembraron `tipos_evidencia` y `archivos_storage` de prueba para usar Swagger sin integración real con R2

### Captura operativa para KPIs

Se agregó la tabla:

* `eventos_operativos_viaje`

Propósito:

* guardar snapshots operativos sin alterar `historial_estatus_viaje`
* habilitar KPIs de kilometraje, diésel y ubicación

Tipos de evento actuales:

* `INICIO_VIAJE`
* `STANDBY`
* `FINALIZACION_VIAJE`

Endpoints afectados:

* `POST /viajes/{id}/iniciar-viaje`
* `POST /viajes/{id}/poner-standby`
* `POST /viajes/{id}/finalizar`

Payload obligatorio en esas acciones:

* `kilometraje`
* `nivel_diesel`
* `ubicacion`
* `latitud` opcional
* `longitud` opcional
* `comentario` opcional

Validaciones:

* `kilometraje >= 0`
* `nivel_diesel` entre `0` y `100`
* `ubicacion` obligatoria y no vacía
* si se envía `latitud`, también debe enviarse `longitud`
* si se envía `longitud`, también debe enviarse `latitud`

Lectura:

* `GET /viajes/{id}/detail` incluye `eventos_operativos`
* `GET /viajes/{id}/eventos-operativos` devuelve la colección explícita

Frontend:

* el panel móvil del operador abre una captura tipo bottom-sheet antes de `iniciar viaje`, `standby` y `finalizar`
* permite usar ubicación actual del navegador si está disponible

### Dashboard de KPIs operativos

Se agregó una capa analítica separada del workflow:

* `GET /viajes/kpis-operativos`

KPIs calculados:

* `total_viajes_con_eventos`
* `km_total_recorridos`
* `km_promedio_por_viaje`
* `diesel_total_consumido_estimado`
* `diesel_promedio_consumido`
* `numero_total_standbys`
* `viajes_finalizados_con_kpi`

Filtros soportados:

* `fecha_desde`
* `fecha_hasta`
* `id_operador`
* `id_cliente`
* `id_estatus`
* `solo_completos`

Autorización:

* `ADMIN` ve todos los KPIs
* `OPERADOR` ve solo sus viajes
* si `OPERADOR` manda `id_operador`, se ignora y se usa su `id_operador`

Tabla por viaje:

* `folio`
* `cliente`
* `operador`
* `km_inicio`
* `km_final`
* `km_recorridos`
* `diesel_inicio`
* `diesel_final`
* `diesel_consumido`
* `numero_standbys`
* `ubicacion_inicio`
* `ubicacion_final`
* `fecha_inicio`
* `fecha_finalizacion`
* `kpi_completo`
* `kpi_valido`
* `anomalia`

Anomalías:

* `EVENTO_INICIO_FALTANTE`
* `EVENTO_FINAL_FALTANTE`
* `KM_FINAL_MENOR_INICIO`
* `DIESEL_FINAL_MAYOR_INICIO`

Frontend:

* nueva ruta `/dashboard/kpis`
* cards resumen en tonos azules
* barra de filtros
* tabla ejecutiva por viaje

### Validación documental estricta implementada

Con `strict_evidence_validation = true`:

* `INICIADO` exige:
  * evidencia válida del viaje
  * al menos un documento vigente del operador actual
  * al menos un documento vigente del tráiler actual
  * al menos un documento vigente de la caja actual, si existe
* `FINALIZADO`:
  * mantiene validación de evidencia
  * valida documentos solo de recursos actuales todavía ligados al viaje
  * deja preparado el camino para endurecer esta regla más adelante

Regla de vigencia:

* `documento.estatus == "VIGENTE"`
* si `tipo_documento.requiere_vigencia = true`, `fecha_expiracion` debe existir y ser mayor o igual a hoy
* si `requiere_vigencia = false`, basta con `estatus = VIGENTE`

Soporte mínimo para pruebas:

* `GET /viajes/catalogos/tipos-documento`
* `POST /viajes/{id}/documentos`
* `GET /viajes/{id}/documentos`
* `POST /viajes/{id}/operador-actual/documentos`
* `GET /viajes/{id}/operador-actual/documentos`
* `POST /viajes/{id}/trailer-actual/documentos`
* `GET /viajes/{id}/trailer-actual/documentos`
* `POST /viajes/{id}/caja-actual/documentos`
* `GET /viajes/{id}/caja-actual/documentos`

---

### 2. Vistas enriquecidas

Actualmente devuelve IDs.

Falta:

* nombres de cliente
* nombre de estatus
* operador actual
* tráiler actual
* caja actual

### Estado implementado parcialmente

Ya existen vistas enriquecidas para:

* `GET /viajes/enriched`
* `GET /viajes/{id}/detail`
* `GET /viajes/{id}/asignaciones/enriched`
* `GET /viajes/{id}/historial-estatus/enriched`

Estas vistas agregan objetos resumidos anidados y mantienen intactos los endpoints planos existentes.

---

### 3. Endpoint catálogo

```
GET /catalogos/estatus
```

---

### 4. Filtros de viajes

* activos
* finalizados
* por operador
* por cliente

---

### 5. Integración con archivos (Cloudflare R2)

* vincular evidencias reales
* validar contenido antes de transición

---

### 6. Seguridad y permisos

Estado implementado:

* `POST /auth/bootstrap-admin`
* `POST /auth/login`
* `GET /auth/me`
* `POST /evidencias/presign-upload`
* JWT con payload mínimo:
  * `sub`
  * `username`
  * `role`
  * `operator_id`
* El bootstrap inicial:
  * detecta si ya existe un usuario con rol `ADMIN`
  * crea el rol `ADMIN` si aún no existe
  * crea el primer usuario administrador usando el hashing actual
  * deja de estar disponible en cuanto ya existe un `ADMIN`
* `ADMIN` accede a rutas administrativas y operativas
* `OPERADOR` accede solo a rutas operativas sobre sus propios viajes
* Para acciones operativas como `FINALIZADO`, el ownership del operador también reconoce asignación histórica si el viaje no está actualmente ligado a otro operador

Primera capa protegida:

* `roles`
* `usuarios`
* rutas operativas y de consulta de viajes

---

## 🎯 Siguiente objetivo recomendado

Implementar:

👉 Subida real de evidencias/documentos y refinamiento de la experiencia mobile operativa

---

## 🧪 Pruebas manuales recomendadas en Swagger

Autenticación:

1. Si la base aún no tiene administrador, ejecutar `POST /auth/bootstrap-admin`
2. Confirmar creación exitosa del primer `ADMIN`
3. Repetir `POST /auth/bootstrap-admin` y confirmar rechazo por bootstrap cerrado
4. Ejecutar `POST /auth/login`
5. Copiar el `access_token`
6. Usar `Authorize` en Swagger con el token Bearer
7. Ejecutar `GET /auth/me` y validar identidad, rol e `id_operador` si aplica

Autorización:

1. Crear viaje
2. Asignar operador + tráiler + caja
3. Consultar `GET /viajes/catalogos/tipos-evidencia`
4. Consultar `GET /viajes/archivos-prueba`
5. Crear evidencia con `POST /viajes/{id}/evidencias`
6. Ejecutar `POST /viajes/{id}/iniciar-carga`
7. Ejecutar `POST /viajes/{id}/iniciar-viaje` y confirmar éxito
8. Ejecutar `POST /viajes/{id}/finalizar` con evidencia válida y confirmar éxito
9. Consultar `GET /viajes/{id}/asignaciones/enriched` y validar recursos anidados
10. Consultar `GET /viajes/{id}/historial-estatus/enriched` y validar estatus y usuario anidados
11. Activar `strict_evidence_validation=true`
12. Intentar `POST /viajes/{id}/iniciar-viaje` sin documentos vigentes del operador o tráiler y confirmar rechazo claro
13. Consultar `GET /viajes/catalogos/tipos-documento`
14. Consultar `GET /viajes/archivos-prueba`
15. Cargar documentos vigentes para operador y tráiler, y para caja si aplica
16. Reintentar `POST /viajes/{id}/iniciar-viaje` y confirmar éxito
17. Ejecutar `POST /viajes/{id}/finalizar` y confirmar que la validación documental solo aplica a recursos actuales presentes
18. Con `ADMIN`, verificar acceso a `/roles` y `/usuarios`
19. Con `OPERADOR`, verificar `403` en `/roles`, `/usuarios` y `POST /viajes`
20. Con `OPERADOR`, verificar acceso a sus propios viajes y `403` en viajes ajenos

---

## 🧠 Nota para Codex

Este proyecto ya tiene:

* estructura sólida
* reglas claras
* separación de capas correcta

Evitar:

* romper lógica existente
* duplicar validaciones

Preferir:

* extender lógica actual
* mantener consistencia del workflow
