"""Public messages never interpolate input, SQL or exception text."""


class AuditEngineError(Exception):
    pass


class AuditDisabledError(AuditEngineError):
    def __init__(self):
        super().__init__("La operación requiere auditoría habilitada")


class AuditPayloadError(AuditEngineError):
    def __init__(self):
        super().__init__("Los datos de auditoría no cumplen el contrato seguro")


class AuditPersistenceError(AuditEngineError):
    def __init__(self):
        super().__init__("PostgreSQL rechazó el evento de auditoría")


class AuditTransactionError(AuditEngineError):
    def __init__(self):
        super().__init__("El estado transaccional no permite esta operación auditora")


class FailureAuditRecordingError(AuditEngineError):
    def __init__(self, business_error=None, cleanup_errors=()):
        super().__init__("No fue posible completar el registro independiente de auditoría")
        self.business_error = business_error
        self.cleanup_errors = tuple(cleanup_errors)
