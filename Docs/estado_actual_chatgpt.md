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
* Si se activa en `true`, se deja preparado el punto de extensión para validación documental
* Si todavía no existen documentos cargados por API, no se rompe el flujo actual
* Ya existe un CRUD base de evidencias anidado bajo viajes para desbloquear pruebas operativas
* Se sembraron `tipos_evidencia` y `archivos_storage` de prueba para usar Swagger sin integración real con R2

---

### 2. Vistas enriquecidas

Actualmente devuelve IDs.

Falta:

* nombres de cliente
* nombre de estatus
* operador actual
* tráiler actual
* caja actual

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

## 🎯 Siguiente objetivo recomendado

Implementar:

👉 Refinar clasificación de evidencias de inicio/cierre y sustituir archivos mock por integración real de almacenamiento

---

## 🧪 Pruebas manuales recomendadas en Swagger

1. Crear viaje
2. Asignar operador + tráiler + caja
3. Consultar `GET /viajes/catalogos/tipos-evidencia`
4. Consultar `GET /viajes/archivos-prueba`
5. Crear evidencia con `POST /viajes/{id}/evidencias`
6. Ejecutar `POST /viajes/{id}/iniciar-carga`
7. Ejecutar `POST /viajes/{id}/iniciar-viaje` y confirmar éxito
8. Ejecutar `POST /viajes/{id}/finalizar` con evidencia válida y confirmar éxito

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
