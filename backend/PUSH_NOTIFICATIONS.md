# Web Push en DAFREQ

Variables requeridas:

```env
WEB_PUSH_ENABLED=true
WEB_PUSH_VAPID_PUBLIC_KEY=
WEB_PUSH_VAPID_PRIVATE_KEY=
WEB_PUSH_SUBJECT=mailto:admin@dafreqlogistica.com
```

En frontend:

```env
NEXT_PUBLIC_WEB_PUSH_PUBLIC_KEY=
```

`NEXT_PUBLIC_WEB_PUSH_PUBLIC_KEY` debe ser igual a `WEB_PUSH_VAPID_PUBLIC_KEY`.

## Generar VAPID keys

Después de instalar dependencias del backend:

```bash
python backend/scripts/generate_vapid_keys.py
```

El script imprime:

- `WEB_PUSH_VAPID_PUBLIC_KEY`
- `WEB_PUSH_VAPID_PRIVATE_KEY`

Usa la public key también en `NEXT_PUBLIC_WEB_PUSH_PUBLIC_KEY`.
