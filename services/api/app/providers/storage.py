"""Private object storage port, with an S3-compatible implementation."""
import hashlib
from dataclasses import dataclass

import boto3
from botocore.config import Config

from app.core.config import get_settings
from app.core.errors import DomainError


MAX_KYC_SIZE = 10 * 1024 * 1024
SUPPORTED_MIME = {
    "application/pdf": b"%PDF-",
    "image/png": bytes.fromhex("89504e470d0a1a0a"),
    "image/jpeg": bytes.fromhex("ffd8ff"),
}


@dataclass(frozen=True, slots=True)
class UploadGrant:
    url: str
    fields: dict
    expires_seconds: int = 300


class StorageProvider:
    def signed_kyc_upload(self, key: str, content_type: str, size: int) -> UploadGrant:
        raise NotImplementedError

    def verify_kyc_object(self, key: str, content_type: str, declared_size: int) -> str:
        raise NotImplementedError

    def signed_private_download(self, key: str, expiry_seconds: int = 300) -> str:
        raise NotImplementedError


class S3StorageProvider(StorageProvider):
    def __init__(self) -> None:
        cfg = get_settings()
        if not cfg.storage_bucket or not cfg.storage_access_key or not cfg.storage_secret_key:
            raise DomainError(
                "DOCUMENT_STORAGE_NOT_CONFIGURED",
                "Private document storage is not configured",
                503,
            )
        if cfg.app_env == "production" and cfg.storage_endpoint and not cfg.storage_endpoint.startswith("https://"):
            raise RuntimeError("Private storage must use HTTPS in production")
        self.bucket = cfg.storage_bucket
        shared = {
            "aws_access_key_id": cfg.storage_access_key,
            "aws_secret_access_key": cfg.storage_secret_key,
            "region_name": cfg.storage_region,
            "config": Config(signature_version="s3v4"),
        }
        self.client = boto3.client("s3", endpoint_url=cfg.storage_endpoint or None, **shared)
        self.public = boto3.client(
            "s3",
            endpoint_url=cfg.storage_public_endpoint or cfg.storage_endpoint or None,
            **shared,
        )
        self.is_production = cfg.app_env == "production"

    def signed_kyc_upload(self, key: str, content_type: str, size: int) -> UploadGrant:
        if content_type not in SUPPORTED_MIME or size < 1 or size > MAX_KYC_SIZE:
            raise DomainError("INVALID_DOCUMENT", "Unsupported document type or size", 422)
        fields = {"Content-Type": content_type}
        conditions = [{"Content-Type": content_type}, ["content-length-range", 1, MAX_KYC_SIZE]]
        if self.is_production:
            fields["x-amz-server-side-encryption"] = "AES256"
            conditions.append({"x-amz-server-side-encryption": "AES256"})
        grant = self.public.generate_presigned_post(
            Bucket=self.bucket,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=300,
        )
        return UploadGrant(url=grant["url"], fields=grant["fields"])

    def verify_kyc_object(self, key: str, content_type: str, declared_size: int) -> str:
        if not key.startswith("kyc/") or content_type not in SUPPORTED_MIME:
            raise DomainError("INVALID_DOCUMENT", "Invalid KYC object", 422)
        try:
            metadata = self.client.head_object(Bucket=self.bucket, Key=key)
            actual_size = metadata["ContentLength"]
            if (
                actual_size != declared_size
                or actual_size < 1
                or actual_size > MAX_KYC_SIZE
                or metadata.get("ContentType") != content_type
            ):
                raise DomainError("DOCUMENT_MISMATCH", "Uploaded document metadata differs", 422)
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"].read(MAX_KYC_SIZE + 1)
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError(
                "DOCUMENT_NOT_AVAILABLE",
                "Uploaded document is unavailable for verification",
                503,
            ) from exc
        if len(body) != actual_size or not body.startswith(SUPPORTED_MIME[content_type]):
            raise DomainError("DOCUMENT_SIGNATURE_MISMATCH", "Document signature is invalid", 422)
        return hashlib.sha256(body).hexdigest()

    def signed_private_download(self, key: str, expiry_seconds: int = 300) -> str:
        if not key.startswith("kyc/"):
            raise DomainError("INVALID_DOCUMENT", "Invalid private document key", 422)
        return self.public.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=min(expiry_seconds, 300),
        )
