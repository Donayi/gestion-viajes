from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps_auth import get_current_user, require_admin
from app.core.config import settings
from app.db.deps import get_db
from app.models.models import PushSubscription, Usuario
from app.schemas.push import (
    PushStatusResponse,
    PushSubscriptionCreate,
    PushSubscriptionResponse,
    PushTestResponse,
    PushUnsubscribeRequest,
)
from app.services.push_service import send_push_to_user, send_push_to_user_detailed


router = APIRouter(prefix="/push", tags=["Push Notifications"])


@router.post("/subscribe", response_model=PushSubscriptionResponse, status_code=status.HTTP_201_CREATED)
def subscribe_push(
    subscription_in: PushSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    endpoint = subscription_in.endpoint.strip()
    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()

    if existing:
        existing.id_usuario = current_user.id_usuario
        existing.p256dh = subscription_in.keys.p256dh.strip()
        existing.auth = subscription_in.keys.auth.strip()
        existing.user_agent = subscription_in.user_agent.strip() if subscription_in.user_agent else None
        existing.activo = True
        db.commit()
        db.refresh(existing)
        return existing

    subscription = PushSubscription(
        id_usuario=current_user.id_usuario,
        endpoint=endpoint,
        p256dh=subscription_in.keys.p256dh.strip(),
        auth=subscription_in.keys.auth.strip(),
        user_agent=subscription_in.user_agent.strip() if subscription_in.user_agent else None,
        activo=True,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@router.delete("/unsubscribe", response_model=PushTestResponse)
def unsubscribe_push(
    payload: PushUnsubscribeRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    subscription = (
        db.query(PushSubscription)
        .filter(
            PushSubscription.endpoint == payload.endpoint.strip(),
            PushSubscription.id_usuario == current_user.id_usuario,
        )
        .first()
    )

    if subscription:
        subscription.activo = False
        db.commit()

    return PushTestResponse(enviado=True, mensaje="Suscripción desactivada")


@router.get("/status", response_model=PushStatusResponse)
def get_push_status(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    active_count = (
        db.query(PushSubscription)
        .filter(
            PushSubscription.id_usuario == current_user.id_usuario,
            PushSubscription.activo.is_(True),
        )
        .count()
    )
    return PushStatusResponse(
        enabled=settings.web_push_enabled,
        vapid_public_key_configured=bool(settings.web_push_vapid_public_key),
        has_active_subscriptions=active_count > 0,
        active_subscriptions_count=active_count,
    )


@router.post("/test", response_model=PushTestResponse)
def send_push_test_current_user(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = send_push_to_user_detailed(
        db,
        current_user.id_usuario,
        "DAFREQ listo para notificar",
        "Las notificaciones del dispositivo ya están activas en este navegador.",
        url="/dashboard",
        data={"id_usuario": current_user.id_usuario},
        tag=f"push-test-{current_user.id_usuario}",
        notification_type="PUSH_TEST",
    )
    return PushTestResponse(
        enviado=bool(result["enviado"]),
        mensaje="Push de prueba enviado" if result["enviado"] else "No fue posible enviar el push de prueba",
        total_subscriptions=int(result["total_subscriptions"]),
        success_count=int(result["success_count"]),
        failure_count=int(result["failure_count"]),
        errores_resumidos=list(result["errores_resumidos"]),
    )


@router.post("/test/{id_usuario}", response_model=PushTestResponse)
def send_push_test_specific_user(
    id_usuario: int,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    user = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    result = send_push_to_user_detailed(
        db,
        id_usuario,
        "Prueba administrativa DAFREQ",
        f"El administrador envió una prueba de notificaciones a {user.nombre}.",
        url="/dashboard",
        data={"id_usuario": id_usuario},
        tag=f"push-test-{id_usuario}",
        notification_type="PUSH_TEST",
    )
    return PushTestResponse(
        enviado=bool(result["enviado"]),
        mensaje="Push de prueba enviado" if result["enviado"] else "No fue posible enviar el push de prueba",
        total_subscriptions=int(result["total_subscriptions"]),
        success_count=int(result["success_count"]),
        failure_count=int(result["failure_count"]),
        errores_resumidos=list(result["errores_resumidos"]),
    )
