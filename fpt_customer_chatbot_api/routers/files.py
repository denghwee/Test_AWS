"""
Files Router - S3 file upload endpoints.
"""

import uuid
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ..config import settings
from ..dependencies import get_current_active_user
from ..models.user import User

router = APIRouter()


def _s3_client():
    client_kwargs = {"region_name": settings.AWS_REGION}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        client_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        client_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    if settings.AWS_SESSION_TOKEN:
        client_kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN
    return boto3.client("s3", **client_kwargs)


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    """Upload a file to the configured private S3 bucket."""
    if not settings.S3_BUCKET_NAME:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3 bucket is not configured.",
        )

    original_name = Path(file.filename or "upload.bin").name
    object_key = f"uploads/users/{current_user.id}/{uuid.uuid4()}-{original_name}"

    extra_args = {}
    if file.content_type:
        extra_args["ContentType"] = file.content_type

    try:
        s3 = _s3_client()
        s3.upload_fileobj(
            file.file,
            settings.S3_BUCKET_NAME,
            object_key,
            ExtraArgs=extra_args or None,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload file to S3: {exc}",
        ) from exc
    finally:
        await file.close()

    return {
        "message": "File uploaded successfully.",
        "bucket": settings.S3_BUCKET_NAME,
        "key": object_key,
        "filename": original_name,
        "content_type": file.content_type,
    }
