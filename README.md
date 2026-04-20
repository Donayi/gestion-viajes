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
4. Iniciar viaje
5. Poner en standby
6. Reasignar
7. Finalizar

---

## ⚠️ Pendientes

* Validación de evidencias obligatorias
* Vistas enriquecidas de viajes
* Filtros avanzados
* Integración completa con almacenamiento (R2)

---

## 👤 Autor

Proyecto desarrollado como base para solución logística empresarial con enfoque en procesos e inteligencia artificial.
