from pathlib import Path
from uuid import uuid4

import boto3

from app.core.config import settings


def _get_endpoint_url() -> str:
    if settings.r2_endpoint_url:
        return settings.r2_endpoint_url

    if settings.r2_account_id:
        return f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"

    raise ValueError("Falta configurar R2_ENDPOINT_URL o R2_ACCOUNT_ID")


def ensure_r2_configured() -> None:
    required_values = {
        "R2_ACCESS_KEY_ID": settings.r2_access_key_id,
        "R2_SECRET_ACCESS_KEY": settings.r2_secret_access_key,
        "R2_BUCKET": settings.r2_bucket,
    }

    missing = [key for key, value in required_values.items() if not value]
    if missing:
        raise ValueError(
            f"Falta configurar almacenamiento R2: {', '.join(missing)}"
        )

    _get_endpoint_url()


def get_r2_client():
    ensure_r2_configured()
    return boto3.client(
        "s3",
        region_name=settings.r2_region,
        endpoint_url=_get_endpoint_url(),
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
    )


def build_evidencia_file_key(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    generated_name = f"{uuid4().hex}{extension}"
    return f"evidencias/{generated_name}"


def generate_presigned_upload_url(file_key: str, content_type: str) -> str:
    client = get_r2_client()
    return client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.r2_bucket,
            "Key": file_key,
            "ContentType": content_type,
        },
        ExpiresIn=settings.r2_presign_expiration_seconds,
    )
