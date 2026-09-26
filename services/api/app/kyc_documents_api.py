"""KYC document intake: signed private uploads and human review gates."""
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError
from app.core.security import get_current_user, require_permissions
from app.lifecycle_models import KycCase, KycDocument
from app.models import User
from app.providers.storage import MAX_KYC_SIZE, SUPPORTED_MIME, S3StorageProvider
from app.services.audit import append_audit

router = APIRouter(prefix="/api/v1")


class DocumentIntent(BaseModel):
    document_type: Literal["DRIVING_LICENSE", "IDENTITY_PROOF", "ADDRESS_PROOF", "OTHER"]
    content_type: Literal["application/pdf", "image/png", "image/jpeg"]
    file_size: int = Field(ge=1, le=MAX_KYC_SIZE)


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    upload_url: str
    fields: dict[str, str]
    expires_seconds: int


class DocumentSummary(BaseModel):
    id: UUID
    document_type: str
    content_type: str
    file_size: int
    status: str


class AdminDocumentSummary(DocumentSummary):
    download_url: str | None = None


class DocumentReview(BaseModel):
    decision: Literal["VERIFIED", "REJECTED"]
    reason: str | None = Field(default=None, max_length=400)


def owner_case(db: Session, case_id: UUID, user_id: UUID) -> KycCase:
    item = db.get(KycCase, case_id)
    if item is None or item.customer_id != user_id:
        raise NotFoundError("KYC case not found")
    return item


@router.post(
    "/kyc/cases/{case_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=201,
)
def request_kyc_upload(
    case_id: UUID,
    payload: DocumentIntent,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    case = owner_case(db, case_id, user.id)
    if case.status not in {"PENDING", "REQUIRED_AGAIN"}:
        raise ConflictError("KYC_LOCKED", "This case cannot accept more documents")
    if payload.content_type not in SUPPORTED_MIME:
        raise HTTPException(status_code=422, detail="Unsupported content type")
    doc_id = uuid4()
    suffix = {
        "application/pdf": "pdf",
        "image/jpeg": "jpg",
        "image/png": "png",
    }[payload.content_type]
    key = f"kyc/{case.id}/{doc_id}.{suffix}"
    grant = S3StorageProvider().signed_kyc_upload(
        key, payload.content_type, payload.file_size
    )
    now = datetime.now(UTC)
    db.add(
        KycDocument(
            id=doc_id, kyc_case_id=case.id, document_type=payload.document_type,
            storage_key=key, content_type=payload.content_type,
            file_size=payload.file_size, checksum_sha256="0" * 64,
            status="REQUESTED", created_at=now, updated_at=now,
        )
    )
    db.commit()
    return DocumentUploadResponse(
        document_id=doc_id,
        upload_url=grant.url,
        fields=grant.fields,
        expires_seconds=grant.expires_seconds,
    )


@router.post("/kyc/documents/{document_id}/confirm", response_model=DocumentSummary)
def confirm_kyc_upload(
    document_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentSummary:
    doc = db.get(KycDocument, document_id, with_for_update=True)
    if doc is None:
        raise NotFoundError("KYC document not found")
    case = owner_case(db, doc.kyc_case_id, user.id)
    if doc.status == "UPLOADED":
        return DocumentSummary.model_validate(doc, from_attributes=True)
    if doc.status != "REQUESTED" or case.status not in {"PENDING", "REQUIRED_AGAIN"}:
        raise ConflictError("KYC_LOCKED", "Document upload cannot be confirmed")
    checksum = S3StorageProvider().verify_kyc_object(
        doc.storage_key, doc.content_type, doc.file_size
    )
    doc.checksum_sha256 = checksum
    doc.status = "UPLOADED"
    doc.updated_at = datetime.now(UTC)
    case.status = "SUBMITTED"
    case.updated_at = datetime.now(UTC)
    db.commit()
    return DocumentSummary.model_validate(doc, from_attributes=True)


@router.get("/kyc/cases/{case_id}/documents", response_model=list[DocumentSummary])
def list_my_kyc_documents(
    case_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentSummary]:
    owner_case(db, case_id, user.id)
    docs = db.scalars(
        select(KycDocument).where(KycDocument.kyc_case_id == case_id)
    ).all()
    return [DocumentSummary.model_validate(doc, from_attributes=True) for doc in docs]


@router.get(
    "/admin/kyc/{case_id}/documents",
    response_model=list[AdminDocumentSummary],
)
def admin_list_kyc_documents(
    case_id: UUID,
    reviewer: User = Depends(require_permissions("kyc:approve")),
    db: Session = Depends(get_db),
) -> list[AdminDocumentSummary]:
    if db.get(KycCase, case_id) is None:
        raise NotFoundError("KYC case not found")
    docs = db.scalars(
        select(KycDocument).where(KycDocument.kyc_case_id == case_id)
    ).all()
    storage = S3StorageProvider()
    return [
        AdminDocumentSummary(
            id=doc.id, document_type=doc.document_type,
            content_type=doc.content_type, file_size=doc.file_size,
            status=doc.status,
            download_url=storage.signed_private_download(doc.storage_key)
            if doc.status in {"UPLOADED", "VERIFIED"} else None,
        )
        for doc in docs
    ]


@router.post(
    "/admin/kyc/documents/{document_id}/review",
    response_model=DocumentSummary,
)
def admin_review_kyc_document(
    document_id: UUID,
    payload: DocumentReview,
    request: Request,
    reviewer: User = Depends(require_permissions("kyc:approve")),
    db: Session = Depends(get_db),
) -> DocumentSummary:
    doc = db.get(KycDocument, document_id, with_for_update=True)
    if doc is None:
        raise NotFoundError("KYC document not found")
    if doc.status != "UPLOADED":
        raise ConflictError("INVALID_KYC_REVIEW", "Only uploaded evidence can be reviewed")
    before = {"status": doc.status}
    doc.status = payload.decision
    doc.updated_at = datetime.now(UTC)
    append_audit(
        db, actor_user_id=reviewer.id,
        action="kyc:document-review", entity="kyc_document",
        entity_id=str(doc.id),
        request_id=getattr(request.state, "request_id", None),
        before_state=before,
        after_state={"status": doc.status, "reason": payload.reason},
    )
    db.commit()
    return DocumentSummary.model_validate(doc, from_attributes=True)
