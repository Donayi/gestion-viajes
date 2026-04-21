# 🚛 Gestión de Viajes - Plataforma Logística

## 📌 Descripción

Sistema backend para la gestión de viajes de transporte, diseñado para controlar:

* Asignación de operadores, tráileres y cajas
* Seguimiento de estatus de viaje
* Evidencias y documentación
* Disponibilidad de recursos en tiempo real

El sistema implementa reglas operativas reales del negocio logístico.

---

## 🧠 Arquitectura

* **Backend:** FastAPI
* **Base de datos:** PostgreSQL
* **ORM:** SQLAlchemy
* **Contenedores:** Docker + Docker Compose

---

## ⚙️ Cómo levantar el proyecto

```bash
docker compose down
docker compose up --build
```

Accesos:

* API: http://localhost:8080
* Swagger: http://localhost:8080/docs

---

## 🗂️ Estructura del proyecto

```
backend/
  app/
    api/
    crud/
    models/
    schemas/
    db/
    seeds/
infra/
  docker-compose.yml
docs/
```

---

## 🧩 Módulos implementados

### Catálogos

* Roles
* Usuarios
* Operadores
* Clientes
* Tráileres
* Cajas

### Core del negocio

* Viajes
* Asignaciones de viaje
* Historial de estatus
* Catálogo de estatus
* Transiciones de estatus

---

## 🔄 Workflow de viajes

Estados principales:

```
CREADO → ASIGNADO → CARGANDO → INICIADO → FINALIZADO
                      ↓
                  RETRASADO
                      ↓
                   STANDBY → reasignación
```

---

## 📌 Reglas de negocio clave

* Un operador no puede estar en dos viajes activos
* Un tráiler no puede estar en dos viajes activos
* Una caja:

  * queda ligada al viaje hasta finalizar
  * no se libera en STANDBY
* En STANDBY:

  * operador y tráiler se liberan
* En FINALIZADO:

  * todos los recursos se liberan
* Las transiciones se controlan mediante tabla (`transiciones_estatus_viaje`)

---

## 🔍 Disponibilidad de recursos

Se calcula dinámicamente (NO se guarda en tablas):

* `/viajes/disponibilidad/operadores`
* `/viajes/disponibilidad/trailers`
* `/viajes/disponibilidad/cajas`

---

## 🚀 Endpoints principales

### Viajes

* `POST /viajes`
* `GET /viajes`
* `GET /viajes/{id}`
* `PUT /viajes/{id}`

### Workflow

* `POST /viajes/{id}/asignar`
* `POST /viajes/{id}/evidencias`
* `GET /viajes/{id}/evidencias`
* `GET /viajes/{id}/evidencias/{evidencia_id}`
* `PUT /viajes/{id}/evidencias/{evidencia_id}`
* `DELETE /viajes/{id}/evidencias/{evidencia_id}`
* `GET /viajes/catalogos/tipos-documento`
* `POST /viajes/{id}/documentos`
* `GET /viajes/{id}/documentos`
* `POST /viajes/{id}/operador-actual/documentos`
* `GET /viajes/{id}/operador-actual/documentos`
* `POST /viajes/{id}/trailer-actual/documentos`
* `GET /viajes/{id}/trailer-actual/documentos`
* `POST /viajes/{id}/caja-actual/documentos`
* `GET /viajes/{id}/caja-actual/documentos`
* `GET /viajes/{id}/asignaciones/enriched`
* `GET /viajes/{id}/historial-estatus/enriched`
* `POST /viajes/{id}/iniciar-carga`
* `POST /viajes/{id}/iniciar-viaje`
* `POST /viajes/{id}/marcar-retraso`
* `POST /viajes/{id}/poner-standby`
* `POST /viajes/{id}/reasignar`
* `POST /viajes/{id}/finalizar`
* `POST /viajes/{id}/cancelar`

---

## 🧪 Prueba recomendada

1. Crear viaje
2. Asignar operador + tráiler + caja
3. Iniciar carga
4. Cargar al menos una evidencia del viaje con `id_archivo` válido
5. Iniciar viaje
6. Poner en standby
7. Reasignar
8. Finalizar

### Validación de evidencias

* La validación quedó centralizada en el cambio de estatus del backend
* Se dispara únicamente cuando la transición tiene `requiere_evidencia = true`
* Para `INICIADO` se exige al menos una evidencia asociada al viaje con `id_archivo` válido
* Para `FINALIZADO` se exige al menos una evidencia asociada al viaje
* `strict_evidence_validation=false` desactiva la validación documental estricta
* `strict_evidence_validation=true` activa validación documental estricta centralizada en backend
* Para `INICIADO` con validación estricta activa:
  * operador actual con al menos un documento vigente
  * tráiler actual con al menos un documento vigente
  * caja actual con al menos un documento vigente, si existe
* Para `FINALIZADO` con validación estricta activa:
  * mantiene validación de evidencia
  * valida documentos solo de los recursos actuales aún ligados al viaje, sin bloquear por recursos ausentes
* El CRUD base de evidencias se expone como submódulo de viajes
* Existe un CRUD mínimo de documentos para asociar documentos al viaje y a los recursos actuales del viaje
* Se incluyen seeds de `tipos_documento` para pruebas operativas mínimas
* Se incluyen seeds de `tipos_evidencia` y `archivos_storage` de prueba para usar Swagger sin integración real con R2
* Existen vistas enriquecidas de lectura para viajes, historial-estatus y asignaciones orientadas a frontend

### Pruebas manuales sugeridas en Swagger

1. Crear un viaje con `POST /viajes`
2. Asignar recursos con `POST /viajes/{id}/asignar`
3. Consultar `GET /viajes/catalogos/tipos-evidencia` y `GET /viajes/archivos-prueba`
4. Crear evidencia con `POST /viajes/{id}/evidencias`
5. Mover el viaje a `CARGANDO` con `POST /viajes/{id}/iniciar-carga`
6. Intentar `POST /viajes/{id}/iniciar-viaje` y confirmar éxito
7. Consultar o editar la evidencia con `GET/PUT /viajes/{id}/evidencias/{evidencia_id}`
8. Intentar `DELETE /viajes/{id}/evidencias/{evidencia_id}` y confirmar que el viaje vuelve a bloquearse si se queda sin evidencias
9. Consultar `GET /viajes/{id}/asignaciones/enriched` y validar operador/tráiler/caja anidados
10. Consultar `GET /viajes/{id}/historial-estatus/enriched` y validar estatus/usuario anidados
11. Con `strict_evidence_validation=true`, intentar `POST /viajes/{id}/iniciar-viaje` sin documentos vigentes del operador o tráiler y confirmar error claro por entidad
12. Consultar `GET /viajes/catalogos/tipos-documento` y `GET /viajes/archivos-prueba`
13. Crear documentos válidos con `POST /viajes/{id}/operador-actual/documentos` y `POST /viajes/{id}/trailer-actual/documentos`
14. Si el viaje tiene caja, crear documento válido con `POST /viajes/{id}/caja-actual/documentos`
15. Reintentar `POST /viajes/{id}/iniciar-viaje` y confirmar éxito
16. Con `strict_evidence_validation=true`, probar `POST /viajes/{id}/finalizar` y confirmar que solo valida documentos de recursos actuales presentes

---

## ⚠️ Pendientes

* Diferenciar evidencia de inicio vs evidencia de cierre
* Vistas enriquecidas de viajes
* Filtros avanzados
* Integración completa con almacenamiento (R2)

---

## 👤 Autor

Proyecto desarrollado como base para solución logística empresarial con enfoque en procesos e inteligencia artificial.
