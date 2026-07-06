# DAFREQ - Desarrollo Local

## Requisitos

- Docker Desktop
- Node.js
- npm
- Git Bash o PowerShell

## Arquitectura local recomendada

Para desarrollo local se recomienda esta separación:

- PostgreSQL + FastAPI con Docker Compose
- Frontend Next.js con `npm run dev`

Esto permite:

- base de datos y API aisladas en contenedores
- recarga rápida del frontend
- validación visual inmediata de cambios

## Variables de entorno

### `infra/.env`

Ejemplo seguro para desarrollo local:

```env
POSTGRES_USER=logistica
POSTGRES_PASSWORD=change-me
POSTGRES_DB=logistica_db
DATABASE_URL=postgresql+psycopg://logistica:change-me@db:5432/logistica_db

SECRET_KEY=change-me
BOOTSTRAP_ADMIN_ENABLED=true
STRICT_EVIDENCE_VALIDATION=false
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_DEFAULT_CHAT_ID=
APP_PUBLIC_URL=http://localhost:3000

WEB_PUSH_ENABLED=false
WEB_PUSH_VAPID_PUBLIC_KEY=
WEB_PUSH_VAPID_PRIVATE_KEY=
WEB_PUSH_SUBJECT=mailto:admin@example.com

R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=
R2_ENDPOINT_URL=
R2_PUBLIC_BASE_URL=
```

Notas:

- No uses secretos reales en local si no son necesarios.
- En Docker Compose, `DATABASE_URL` debe usar `db:5432`, no `localhost`.
- `BOOTSTRAP_ADMIN_ENABLED=true` sirve para crear el admin inicial en local.

### `frontend/.env.local`

Ejemplo seguro:

```env
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_WEB_PUSH_PUBLIC_KEY=
```

Notas:

- En desarrollo local conviene apuntar directo al backend en `http://localhost:8080`.
- No dejes `NEXT_PUBLIC_API_URL=/api` a menos que también configures un proxy o rewrite en Next.js.

## Cómo levantar backend + DB

Desde la raíz del proyecto:

```powershell
docker compose -f infra/compose.dev.yml --env-file infra/.env up --build
```

Esto levanta:

- PostgreSQL en `localhost:5432`
- FastAPI en `http://localhost:8080`

## Cómo validar backend

Verifica estos endpoints:

- [http://localhost:8080/health](http://localhost:8080/health)
- [http://localhost:8080/docs](http://localhost:8080/docs)

También puedes probar con:

```powershell
curl http://localhost:8080/health
```

## Cómo levantar frontend

En otra terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Frontend local:

- [http://localhost:3000](http://localhost:3000)

## Cómo crear admin local

Si la base está limpia y no existe un administrador, crea uno con el endpoint de bootstrap.

Ejemplo con PowerShell:

```powershell
curl -Method POST http://localhost:8080/auth/bootstrap-admin `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"username":"AdminGeneral","password":"secreto123","nombre":"Admin","apellido":"General"}'
```

Ejemplo con `curl` estilo Bash:

```bash
curl -X POST "http://localhost:8080/auth/bootstrap-admin" \
  -H "Content-Type: application/json" \
  -d '{"username":"AdminGeneral","password":"secreto123","nombre":"Admin","apellido":"General"}'
```

## Cómo iniciar sesión

Una vez creado el administrador local:

- usuario: `AdminGeneral`
- password: `secreto123`

Login web:

- [http://localhost:3000/login](http://localhost:3000/login)

## Cómo ejecutar pruebas

Backend:

```powershell
cd backend
python -m pytest
```

Si usas entorno virtual, actívalo antes de correr pruebas.

## Comandos útiles Docker

Ver contenedores corriendo:

```powershell
docker compose -f infra/compose.dev.yml --env-file infra/.env ps
```

Ver logs de la API:

```powershell
docker compose -f infra/compose.dev.yml --env-file infra/.env logs -f api
```

Ver logs de la base de datos:

```powershell
docker compose -f infra/compose.dev.yml --env-file infra/.env logs -f db
```

Bajar contenedores:

```powershell
docker compose -f infra/compose.dev.yml --env-file infra/.env down
```

Bajar contenedores y eliminar volumen de datos:

```powershell
docker compose -f infra/compose.dev.yml --env-file infra/.env down -v
```

Usa `down -v` solo cuando quieras reiniciar completamente la base local.

## Errores comunes

### `frontend/.env.local` no existe

Síntoma:

- el frontend no conecta con la API
- aparecen errores de red o login

Solución:

- crea `frontend/.env.local`
- define `NEXT_PUBLIC_API_URL=http://localhost:8080`

### CORS mal configurado

Síntoma:

- el navegador bloquea llamadas desde `localhost:3000`

Solución:

- revisa `infra/.env`
- usa:
  `CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`

### `DATABASE_URL` con `db` vs `localhost`

Regla:

- dentro de Docker, el backend debe usar `db:5432`
- fuera de Docker, herramientas locales podrían usar `localhost:5432`

Si el backend corre en Compose, no cambies `db` por `localhost`.

### Docker Desktop apagado

Síntoma:

- `docker compose` falla al iniciar
- no aparecen contenedores

Solución:

- abre Docker Desktop
- espera a que quede completamente iniciado

### Contraseña de PostgreSQL con volumen viejo

Síntoma:

- cambiaste `POSTGRES_PASSWORD`, pero el contenedor sigue rechazando acceso

Causa:

- el volumen de PostgreSQL conserva la inicialización anterior

Solución:

1. baja contenedores
2. elimina volumen local con:

```powershell
docker compose -f infra/compose.dev.yml --env-file infra/.env down -v
```

3. vuelve a levantar con `up --build`

## Flujo recomendado de validación local

1. Levanta backend + DB con Docker Compose.
2. Valida `health` y `docs`.
3. Levanta frontend con `npm run dev`.
4. Crea admin local si la base está limpia.
5. Inicia sesión y valida el ajuste que estés trabajando.
6. Ejecuta pruebas backend si tocaste lógica sensible.
