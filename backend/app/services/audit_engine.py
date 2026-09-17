"""Explicit PostgreSQL coordinator, not automatic instrumentation.

Success never commits or rolls back. The caller commits ONLY after success().
On a known pre-commit failure the caller explicitly invokes rollback_business()
before failure(). A commit with uncertain network outcome must be reconciled;
never automatically call failure() for it. SQL atomicity excludes external effects.
No Session listeners, commit interception or global Session configuration.
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.crud import crud_bitacora
from app.schemas.audit_context import AuditContext
from app.schemas.bitacora import (
    ActorBitacora, BitacoraEventoCreateInternal, ReferenciaRegistroBitacora,
    normalize_audit_username, sanitize_user_agent,
)
from app.services.audit_errors import (
    AuditEngineError, AuditDisabledError, AuditPayloadError, AuditPersistenceError,
    AuditTransactionError, FailureAuditRecordingError,
)
from app.services.audit_payloads import copy_audit_payloads, validate_audit_string


class AuditRequirement(StrEnum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"


@dataclass(frozen=True)
class AuditResult:
    event_id: UUID | None
    skipped: bool
    # Success is pending the caller's commit; independent records are committed.
    committed: bool


def _copy_context(context):
    if not isinstance(context, AuditContext):
        raise AuditPayloadError()
    try:
        actor = context.actor
        for value in (actor.username_snapshot, actor.nombre_snapshot, actor.rol_snapshot):
            validate_audit_string(value)
        copied_actor = ActorBitacora(
            tipo=actor.tipo, usuario_id=actor.usuario_id,
            username_snapshot=actor.username_snapshot, nombre_snapshot=actor.nombre_snapshot,
            rol_snapshot=actor.rol_snapshot,
        )
        for value in (
            copied_actor.username_snapshot, copied_actor.nombre_snapshot,
            copied_actor.rol_snapshot, context.metodo_http, context.ruta_http,
        ):
            validate_audit_string(value)
        return AuditContext(
            actor=copied_actor, request_id=context.request_id, correlation_id=context.correlation_id,
            ip_hash=context.ip_hash, ip_hash_version=context.ip_hash_version,
            user_agent=sanitize_user_agent(context.user_agent),
            metodo_http=context.metodo_http, ruta_http=context.ruta_http,
        )
    except (ValidationError, TypeError, ValueError, AttributeError) as exc:
        raise AuditPayloadError() from exc


def _create(session, event):
    try:
        return crud_bitacora.create_bitacora_evento(session, event)
    except Exception as exc:
        # flush also processes BUSINESS changes. Classify only a named audit constraint.
        diagnostic = getattr(getattr(exc, "orig", None), "diag", None)
        constraint = getattr(diagnostic, "constraint_name", None)
        table = getattr(diagnostic, "table_name", None)
        schema = getattr(diagnostic, "schema_name", None)
        if isinstance(exc, IntegrityError) and table == "bitacora_eventos" and schema == "public" and constraint:
            raise AuditPersistenceError() from exc
        # Generic safe boundary, without claiming an audit origin for a business flush.
        raise AuditEngineError("No fue posible completar el flush transaccional") from exc


class AuditEngine:
    """Factory must return a fresh, clean Engine-bound Session owned by this call.

    Configuration is captured at construction. Required operations must enter
    operation() BEFORE business mutation; committing caller code bypassing that
    explicit protocol is outside this coordinator's guarantee. Functional Sessions
    must use one Engine; external Connection transactions and multibind routing
    are not supported. Each independent factory call transfers ownership.
    """
    def __init__(self, *, config=settings, session_factory=None):
        self.enabled = config.audit_enabled
        self.max_document_bytes = config.audit_max_json_bytes
        self.session_factory = session_factory

    def _enabled_for(self, requirement):
        try:
            requirement = AuditRequirement(requirement)
        except (ValueError, TypeError) as exc:
            raise AuditTransactionError() from exc
        if not self.enabled and requirement is AuditRequirement.REQUIRED:
            raise AuditDisabledError()
        return self.enabled

    def operation(self, session, context, *, requirement=AuditRequirement.REQUIRED):
        # Check BEFORE creating the operation/root transaction or invoking caller business.
        enabled = self._enabled_for(requirement)
        return AuditedOperation(self, session, _copy_context(context) if enabled else None, enabled)

    def _event(
        self, context, *, resultado, categoria, modulo, accion,
        entidad_tipo=None, entidad_id=None, valores_anteriores=None,
        valores_posteriores=None, datos_evento=None, error_codigo=None,
        evento_relacionado_id=None,
    ):
        context = _copy_context(context)
        payloads = copy_audit_payloads(
            valores_anteriores=valores_anteriores, valores_posteriores=valores_posteriores,
            datos_evento=datos_evento, max_document_bytes=self.max_document_bytes,
        )
        try:
            for value in (categoria, modulo, accion, entidad_tipo, entidad_id, error_codigo):
                validate_audit_string(value)
            entidad = None
            if entidad_tipo is not None or entidad_id is not None:
                entidad = ReferenciaRegistroBitacora(entidad_tipo=entidad_tipo, entidad_id=entidad_id)
            for value in (entidad.entidad_id if entidad else None, error_codigo):
                validate_audit_string(value)
            return BitacoraEventoCreateInternal(
                categoria=categoria, modulo=modulo, accion=accion, resultado=resultado,
                entidad=entidad, actor=context.actor,
                actor_username_normalizado=(
                    normalize_audit_username(context.actor.username_snapshot)
                    if context.actor.username_snapshot is not None else None
                ),
                request_id=context.request_id, correlation_id=context.correlation_id,
                ip_hash=context.ip_hash, ip_hash_version=context.ip_hash_version,
                user_agent=context.user_agent, metodo_http=context.metodo_http,
                ruta_template=context.ruta_http, schema_version=1,
                valores_anteriores=payloads.valores_anteriores,
                valores_posteriores=payloads.valores_posteriores,
                datos_evento=payloads.datos_evento, error_codigo=error_codigo,
                evento_relacionado_id=evento_relacionado_id,
            )
        except (ValidationError, TypeError, ValueError) as exc:
            raise AuditPayloadError() from exc

    def record_rejected(
        self, context, *, functional_session,
        requirement=AuditRequirement.REQUIRED, **event_data,
    ):
        """Pass the clean functional Session, or explicitly None if none exists."""
        if not self._enabled_for(requirement):
            return AuditResult(None, True, False)
        if functional_session is not None:
            _require_clean(functional_session)
        return self._independent(
            _copy_context(context), "RECHAZADO", functional_session, None, event_data,
        )

    def _independent(self, context, outcome, functional_session, business_error, event_data):
        try:
            event = self._event(context, resultado=outcome, **event_data)
            if self.session_factory is None:
                from app.db.database import SessionLocal

                factory = SessionLocal
            else:
                factory = self.session_factory
            independent = factory()
        except Exception as exc:
            raise FailureAuditRecordingError(business_error) from exc
        # Never close/rollback the caller's Session if a broken factory returns it.
        if independent is functional_session:
            raise FailureAuditRecordingError(business_error) from AuditTransactionError()
        primary_error = None
        cleanup_errors = []
        result = None
        owned_transaction = False
        try:
            _require_clean(independent)
            if not isinstance(independent.get_bind(), Engine):
                raise AuditTransactionError()
            if functional_session is not None and independent.get_bind() is not functional_session.get_bind():
                raise AuditTransactionError()
            owned_transaction = True
            created = _create(independent, event)
            event_id = created.id_evento
            independent.commit()
            result = AuditResult(event_id, False, True)
        except Exception as exc:
            primary_error = exc
            if owned_transaction:
                try:
                    independent.rollback()
                except Exception as cleanup:
                    cleanup_errors.append(cleanup)
        finally:
            try:
                independent.close()
            except Exception as cleanup:
                cleanup_errors.append(cleanup)
        if primary_error is not None or cleanup_errors:
            raise FailureAuditRecordingError(business_error, cleanup_errors) from (
                primary_error if primary_error is not None else cleanup_errors[0]
            )
        return result


def _require_clean(session):
    if not session.is_active or session.in_transaction() or session.new or session.dirty or session.deleted:
        raise AuditTransactionError()


class AuditedOperation:
    """One explicit operation, one root transaction, no implicit finalization.

    rollback_business() is an EXPLICIT caller request, and produces internal
    rollback evidence; an ended transaction alone cannot distinguish commit.
    Do not use it to classify an uncertain commit outcome as a business failure.
    """

    def __init__(self, engine, session, context, enabled):
        if not session.is_active or session.in_nested_transaction():
            raise AuditTransactionError()
        try:
            if not isinstance(session.get_bind(), Engine):
                raise AuditTransactionError()
        except AuditTransactionError:
            raise
        except Exception as exc:
            raise AuditTransactionError() from exc
        self.engine = engine
        self.session = session
        self.context = context
        self.enabled = enabled
        self.transaction = session.get_transaction() or session.begin()
        self.completed = False
        self.rolled_back = False
        self.attempted = False
        self.failure_attempted = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is None and not (self.completed or self.rolled_back):
            raise AuditTransactionError()
        # No inference from exception type/status, and no hidden rollback/commit.
        return False

    def success(self, **event_data):
        if (
            self.attempted or self.rolled_back or not self.session.is_active
            or self.session.in_nested_transaction()
            or self.session.get_transaction() is not self.transaction
        ):
            raise AuditTransactionError()
        self.attempted = True
        if not self.enabled:
            self.completed = True
            return AuditResult(None, True, False)
        event = self.engine._event(self.context, resultado="EXITOSO", **event_data)
        created = _create(self.session, event)
        self.completed = True
        return AuditResult(created.id_evento, False, False)

    def rollback_business(self):
        if self.rolled_back or self.session.get_transaction() is not self.transaction:
            raise AuditTransactionError()
        self.session.rollback()
        _require_clean(self.session)
        self.rolled_back = True
        self.completed = False

    def failure(self, business_error, **event_data):
        if not self.rolled_back or self.completed or self.failure_attempted:
            raise AuditTransactionError()
        _require_clean(self.session)
        self.failure_attempted = True
        if not self.enabled:
            self.completed = True
            return AuditResult(None, True, False)
        result = self.engine._independent(
            self.context, "FALLIDO", self.session, business_error, event_data,
        )
        self.completed = True
        return result


__all__ = ["AuditEngine", "AuditRequirement", "AuditResult", "AuditedOperation"]
