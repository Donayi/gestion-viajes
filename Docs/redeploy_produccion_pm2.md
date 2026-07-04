# Redespliegue de Producción con PM2

## Arquitectura objetivo

- `backend` + `db` con Docker Compose
- `frontend` fuera de contenedor
- `frontend` servido con `PM2`
- `NGINX` como punto de entrada público

## Componentes

### Backend + DB

Usar:

- [infra/compose.prod.yml](D:/Proyecto Daniel - Logistica/gestion-viajes/infra/compose.prod.yml)
- [infra/.env.example](D:/Proyecto Daniel - Logistica/gestion-viajes/infra/.env.example)

El backend queda escuchando en:

- `127.0.0.1:8080`

PostgreSQL queda solo en red interna Docker:

- `db:5432`

### Frontend

El frontend no se containeriza en producción.

Usar:

- [frontend/package.json](D:/Proyecto Daniel - Logistica/gestion-viajes/frontend/package.json)
- [frontend/.env.example](D:/Proyecto Daniel - Logistica/gestion-viajes/frontend/.env.example)

El frontend debe compilarse y arrancarse con PM2 en:

- `127.0.0.1:3000`

### NGINX

Usar como referencia:

- [infra/nginx/dafreqlogistica.conf.example](D:/Proyecto Daniel - Logistica/gestion-viajes/infra/nginx/dafreqlogistica.conf.example)

Rutas:

- `/api/` → `127.0.0.1:8080`
- `/` → `127.0.0.1:3000`

## Flujo operativo recomendado

### 1. Preparar variables

Crear archivo real local del servidor a partir de:

- `infra/.env.example`

Crear archivo real del frontend a partir de:

- `frontend/.env.example`

### 2. Levantar backend + DB

Desde [infra](D:/Proyecto Daniel - Logistica/gestion-viajes/infra):

```bash
docker compose -f compose.prod.yml --env-file .env up -d --build
```

### 3. Compilar frontend

Desde [frontend](D:/Proyecto Daniel - Logistica/gestion-viajes/frontend):

```bash
npm ci
npm run build
```

### 4. Arrancar frontend con PM2

Ejemplo:

```bash
pm2 start npm --name dafreq-frontend -- start
pm2 save
pm2 startup
```

Esto ejecuta:

```bash
npm run start
```

### 5. Configurar NGINX

Apuntar:

- frontend a `127.0.0.1:3000`
- backend a `127.0.0.1:8080`

### 6. Verificaciones mínimas

Backend:

```bash
curl http://127.0.0.1:8080/docs
```

Frontend:

```bash
curl http://127.0.0.1:3000
```

Sitio público:

```bash
curl https://dafreqlogistica.com
```

## Reinicio y mantenimiento

Backend:

```bash
docker compose -f compose.prod.yml --env-file .env restart
```

Frontend:

```bash
pm2 restart dafreq-frontend
```

Logs:

```bash
pm2 logs dafreq-frontend
docker logs --tail 200 logistica_api
```

## Notas

- No reutilizar `.env` viejos con secretos previos
- Rotar credenciales antes del redeploy final
- No exponer PostgreSQL públicamente
- No exponer FastAPI fuera de localhost si NGINX corre en el host
