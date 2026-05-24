import base64
import json
from datetime import datetime

from sqlalchemy.orm import Session, joinedload
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.api.deps_auth import is_admin_role_name, is_mantenimiento_role_name, normalize_role_name
from app.core.config import settings
from app.models.models import Alerta, Operador, PushSubscription, Usuario, Viaje

try:
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover - runtime fallback when dependency is missing
    WebPushException = Exception
    webpush = None


def _push_enabled() -> bool:
    return bool(
        settings.web_push_enabled
        and settings.web_push_vapid_public_key
        and settings.web_push_vapid_private_key
    )


def _decode_b64url(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def _get_vapid_private_key_pem() -> bytes | None:
    if not settings.web_push_vapid_private_key:
        return None

    try:
        private_bytes = _decode_b64url(settings.web_push_vapid_private_key)
        private_int = int.from_bytes(private_bytes, "big")
        private_key = ec.derive_private_key(private_int, ec.SECP256R1())
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    except Exception:
        return None


def _touch_subscription_success(subscription: PushSubscription) -> None:
    subscription.last_success_at = datetime.utcnow()
    subscription.failure_count = 0


def _touch_subscription_failure(subscription: PushSubscription, *, deactivate: bool = False) -> None:
    subscription.last_failure_at = datetime.utcnow()
    subscription.failure_count = (subscription.failure_count or 0) + 1
    if deactivate:
        subscription.activo = False


def _build_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    app_url = (settings.app_public_url or "").rstrip("/")
    if not app_url:
        return path
    return f"{app_url}{path if path.startswith('/') else f'/{path}'}"


def send_push_to_subscription(
    db: Session,
    subscription: PushSubscription,
    *,
    title: str,
    body: str,
    url: str | None = None,
    data: dict[str, object] | None = None,
    tag: str | None = None,
    notification_type: str | None = None,
) -> bool:
    if not _push_enabled() or webpush is None or not subscription.activo:
        return False
    vapid_private_key = _get_vapid_private_key_pem()
    if vapid_private_key is None:
        return False

    payload = {
        "title": title,
        "body": body,
        "url": _build_url(url),
        "tag": tag,
        "type": notification_type,
        "data": data or {},
    }

    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh,
                    "auth": subscription.auth,
                },
            },
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=vapid_private_key,
            vapid_claims={"sub": settings.web_push_subject},
        )
        _touch_subscription_success(subscription)
        db.commit()
        return True
    except WebPushException as exc:  # pragma: no cover - depends on external service
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        _touch_subscription_failure(subscription, deactivate=status_code in {404, 410})
        db.commit()
        return False
    except Exception:  # pragma: no cover - depends on external service
        _touch_subscription_failure(subscription)
        db.commit()
        return False


def send_push_to_user(
    db: Session,
    id_usuario: int,
    title: str,
    body: str,
    url: str | None = None,
    data: dict[str, object] | None = None,
    tag: str | None = None,
    notification_type: str | None = None,
) -> bool:
    if not _push_enabled():
        return False

    subscriptions = (
        db.query(PushSubscription)
        .filter(
            PushSubscription.id_usuario == id_usuario,
            PushSubscription.activo.is_(True),
        )
        .order_by(PushSubscription.updated_at.desc(), PushSubscription.id_subscription.desc())
        .all()
    )

    sent_any = False
    for subscription in subscriptions:
        if send_push_to_subscription(
            db,
            subscription,
            title=title,
            body=body,
            url=url,
            data=data,
            tag=tag,
            notification_type=notification_type,
        ):
            sent_any = True
    return sent_any


def send_push_to_role(
    db: Session,
    rol: str,
    title: str,
    body: str,
    url: str | None = None,
    data: dict[str, object] | None = None,
    tag: str | None = None,
    notification_type: str | None = None,
) -> bool:
    normalized = normalize_role_name(rol)
    users = (
        db.query(Usuario)
        .options(joinedload(Usuario.rol))
        .filter(Usuario.activo.is_(True))
        .all()
    )

    target_users = [
        user for user in users
        if (
            is_admin_role_name(user.rol.nombre) if normalized == "ADMIN"
            else is_mantenimiento_role_name(user.rol.nombre) if normalized == "MANTENIMIENTO"
            else normalize_role_name(user.rol.nombre) == normalized
        )
    ]

    sent_any = False
    for user in target_users:
        if send_push_to_user(
            db,
            user.id_usuario,
            title,
            body,
            url=url,
            data=data,
            tag=tag,
            notification_type=notification_type,
        ):
            sent_any = True
    return sent_any


def send_push_to_admins(
    db: Session,
    title: str,
    body: str,
    url: str | None = None,
    data: dict[str, object] | None = None,
    tag: str | None = None,
    notification_type: str | None = None,
) -> bool:
    return send_push_to_role(
        db,
        "ADMIN",
        title,
        body,
        url=url,
        data=data,
        tag=tag,
        notification_type=notification_type,
    )


def _push_body_from_message(message: str) -> str:
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    if not lines:
        return "Hay una nueva actualización en DAFREQ."
    return " · ".join(lines[:3])


def send_push_for_alert(db: Session, alerta: Alerta) -> bool:
    if not _push_enabled():
        return False

    url = None
    data: dict[str, object] = {"entidad_tipo": alerta.entidad_tipo, "entidad_id": alerta.entidad_id}
    sent_any = False

    if alerta.tipo_alerta in {"VIAJE_CREADO", "VIAJE_ESTATUS_CAMBIO", "STANDBY_SOLICITADO", "VIAJE_ASIGNADO"}:
        viaje = (
            db.query(Viaje)
            .options(joinedload(Viaje.operador_actual).joinedload(Operador.usuario))
            .filter(Viaje.id_viaje == alerta.entidad_id)
            .first()
        )
        url = f"/viajes/{alerta.entidad_id}"
        data["id_viaje"] = alerta.entidad_id
        title = alerta.tipo_alerta.replace("_", " ")
        body = _push_body_from_message(alerta.mensaje)

        if alerta.tipo_alerta == "VIAJE_CREADO":
            sent_any = send_push_to_admins(db, title, body, url=url, data=data, tag=f"viaje-{alerta.entidad_id}", notification_type=alerta.tipo_alerta)
        elif alerta.tipo_alerta == "VIAJE_ASIGNADO":
            if viaje and viaje.operador_actual and viaje.operador_actual.usuario:
                if send_push_to_user(
                    db,
                    viaje.operador_actual.usuario.id_usuario,
                    "Viaje asignado",
                    body,
                    url=url,
                    data=data,
                    tag=f"viaje-{alerta.entidad_id}",
                    notification_type=alerta.tipo_alerta,
                ):
                    sent_any = True
            if send_push_to_admins(db, title, body, url=url, data=data, tag=f"viaje-{alerta.entidad_id}", notification_type=alerta.tipo_alerta):
                sent_any = True
        elif alerta.tipo_alerta == "VIAJE_ESTATUS_CAMBIO":
            if send_push_to_admins(db, title, body, url=url, data=data, tag=f"viaje-{alerta.entidad_id}", notification_type=alerta.tipo_alerta):
                sent_any = True
            if viaje and viaje.operador_actual and viaje.operador_actual.usuario:
                if send_push_to_user(
                    db,
                    viaje.operador_actual.usuario.id_usuario,
                    "Cambio de estatus del viaje",
                    body,
                    url=url,
                    data=data,
                    tag=f"viaje-{alerta.entidad_id}",
                    notification_type=alerta.tipo_alerta,
                ):
                    sent_any = True
        else:
            sent_any = send_push_to_admins(
                db,
                "Solicitud de standby",
                body,
                url=url,
                data=data,
                tag=f"viaje-{alerta.entidad_id}",
                notification_type=alerta.tipo_alerta,
            )
        return sent_any

    if alerta.tipo_alerta == "MANTENIMIENTO_ENTRADA":
        url = "/admin/mantenimientos"
        title = "Mantenimiento activo"
        body = _push_body_from_message(alerta.mensaje)
        if send_push_to_admins(db, title, body, url=url, data=data, tag=f"mantenimiento-{alerta.entidad_id}", notification_type=alerta.tipo_alerta):
            sent_any = True
        if send_push_to_role(db, "MANTENIMIENTO", title, body, url=url, data=data, tag=f"mantenimiento-{alerta.entidad_id}", notification_type=alerta.tipo_alerta):
            sent_any = True
        return sent_any

    if alerta.tipo_alerta in {"DOCUMENTO_POR_VENCER", "DOCUMENTO_VENCIDO", "MANTENIMIENTO_PROXIMO"}:
        return send_push_to_admins(
            db,
            alerta.tipo_alerta.replace("_", " "),
            _push_body_from_message(alerta.mensaje),
            url="/admin/alertas",
            data=data,
            tag=f"alerta-{alerta.id_alerta}",
            notification_type=alerta.tipo_alerta,
        )

    return False
