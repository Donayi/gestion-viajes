import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.api.deps_auth import is_admin_role_name, is_mantenimiento_role_name, normalize_role_name
from app.core.config import settings
from app.models.models import Alerta, Operador, PushSubscription, Usuario, Viaje

try:
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover - runtime fallback when dependency is missing
    WebPushException = Exception
    webpush = None


logger = logging.getLogger(__name__)


def _push_enabled() -> bool:
    return bool(
        settings.web_push_enabled
        and settings.web_push_vapid_public_key
        and settings.web_push_vapid_private_key
    )


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


def _mask_endpoint(endpoint: str | None) -> str:
    if not endpoint:
        return "sin-endpoint"
    if len(endpoint) <= 48:
        return endpoint
    return f"{endpoint[:24]}...{endpoint[-16:]}"


def _extract_error_body(response: object | None) -> str | None:
    if response is None:
        return None

    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()[:300]

    content = getattr(response, "content", None)
    if isinstance(content, bytes) and content:
        try:
            return content.decode("utf-8", errors="ignore").strip()[:300]
        except Exception:
            return None

    return None


def _build_error_summary(
    *,
    kind: str,
    subscription: PushSubscription,
    status_code: int | None = None,
    detail: str | None = None,
    exception_message: str | None = None,
) -> str:
    parts = [f"{kind} subscription={subscription.id_subscription}", f"user={subscription.id_usuario}"]
    if status_code is not None:
        parts.append(f"status={status_code}")
    if detail:
        parts.append(f"detail={detail}")
    elif exception_message:
        parts.append(f"detail={exception_message}")
    return " | ".join(parts)


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
    diagnostics: list[str] | None = None,
) -> bool:
    if not _push_enabled() or webpush is None or not subscription.activo:
        if diagnostics is not None:
            diagnostics.append(
                _build_error_summary(
                    kind="push-disabled",
                    subscription=subscription,
                    detail="Push deshabilitado, sin pywebpush o suscripción inactiva",
                )
            )
        return False

    private_key = settings.web_push_vapid_private_key.strip() if settings.web_push_vapid_private_key else ""

    if not private_key:
        summary = _build_error_summary(
            kind="missing-vapid-private-key",
            subscription=subscription,
            detail="WEB_PUSH_VAPID_PRIVATE_KEY missing",
        )
        logger.error(
            "WEB_PUSH_VAPID_PRIVATE_KEY missing | subscription=%s | user=%s | endpoint=%s",
            subscription.id_subscription,
            subscription.id_usuario,
            _mask_endpoint(subscription.endpoint),
        )
        if diagnostics is not None:
            diagnostics.append(summary)
        return False

    if not settings.web_push_subject:
        summary = _build_error_summary(
            kind="missing-vapid-subject",
            subscription=subscription,
            detail="WEB_PUSH_SUBJECT missing",
        )
        logger.error(
            "WEB_PUSH_SUBJECT missing | subscription=%s | user=%s | endpoint=%s",
            subscription.id_subscription,
            subscription.id_usuario,
            _mask_endpoint(subscription.endpoint),
        )
        if diagnostics is not None:
            diagnostics.append(summary)
        return False

    payload = {
        "title": title,
        "body": body,
        "url": _build_url(url),
        "tag": tag,
        "type": notification_type,
        "data": data or {},
    }

    logger.info(
        "Sending Web Push | enabled=%s | has_private_key=%s | private_key_type=%s | subject=%s | subscription=%s | user=%s | endpoint=%s",
        settings.web_push_enabled,
        bool(private_key),
        type(private_key).__name__,
        settings.web_push_subject,
        subscription.id_subscription,
        subscription.id_usuario,
        _mask_endpoint(subscription.endpoint),
    )

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
            vapid_private_key=private_key,
            vapid_claims={"sub": settings.web_push_subject},
        )
        _touch_subscription_success(subscription)
        db.commit()
        return True
    except WebPushException as exc:  # pragma: no cover - depends on external service
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
        body = _extract_error_body(response)
        summary = _build_error_summary(
            kind="webpush-error",
            subscription=subscription,
            status_code=status_code,
            detail=body,
            exception_message=str(exc),
        )
        logger.warning(
            "WebPushException | subscription=%s | user=%s | endpoint=%s | status=%s | body=%s | error=%s",
            subscription.id_subscription,
            subscription.id_usuario,
            _mask_endpoint(subscription.endpoint),
            status_code,
            body,
            str(exc),
        )
        if diagnostics is not None:
            diagnostics.append(summary)
        _touch_subscription_failure(subscription, deactivate=status_code in {404, 410})
        db.commit()
        return False
    except Exception:  # pragma: no cover - depends on external service
        summary = _build_error_summary(
            kind="push-error",
            subscription=subscription,
            exception_message="Error inesperado durante el envío push",
        )
        logger.exception(
            "Push send failed | subscription=%s | user=%s | endpoint=%s",
            subscription.id_subscription,
            subscription.id_usuario,
            _mask_endpoint(subscription.endpoint),
        )
        if diagnostics is not None:
            diagnostics.append(summary)
        _touch_subscription_failure(subscription)
        db.commit()
        return False


def send_push_to_user_detailed(
    db: Session,
    id_usuario: int,
    title: str,
    body: str,
    url: str | None = None,
    data: dict[str, object] | None = None,
    tag: str | None = None,
    notification_type: str | None = None,
) -> dict[str, object]:
    subscriptions = (
        db.query(PushSubscription)
        .filter(
            PushSubscription.id_usuario == id_usuario,
            PushSubscription.activo.is_(True),
        )
        .order_by(PushSubscription.updated_at.desc(), PushSubscription.id_subscription.desc())
        .all()
    )

    diagnostics: list[str] = []
    success_count = 0
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
            diagnostics=diagnostics,
        ):
            success_count += 1

    return {
        "enviado": success_count > 0,
        "total_subscriptions": len(subscriptions),
        "success_count": success_count,
        "failure_count": max(len(subscriptions) - success_count, 0),
        "errores_resumidos": diagnostics,
    }


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
    result = send_push_to_user_detailed(
        db,
        id_usuario,
        title,
        body,
        url=url,
        data=data,
        tag=tag,
        notification_type=notification_type,
    )
    return bool(result["enviado"])


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
