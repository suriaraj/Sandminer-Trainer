import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError
from app.core.security import get_current_user, require_permissions
from app.lifecycle_models import (
    DamageRecord,
    Deposit,
    HandoverRecord,
    InspectionRecord,
    KycCase,
    Review,
    SupportTicket,
)
from app.lifecycle_schemas import (
    BookingTransitionRequest,
    DamageCreateRequest,
    DamageResponse,
    DepositResponse,
    HandoverCreateRequest,
    HandoverResponse,
    InspectionCreateRequest,
    InspectionResponse,
    KycCaseCreateRequest,
    KycCaseResponse,
    KycReviewRequest,
    PaymentInitiateResponse,
    ReviewCreateRequest,
    ReviewResponse,
    SandboxWebhookEvent,
    SupportTicketCreateRequest,
    SupportTicketResponse,
)
from app.models import (
    Booking,
    BookingStatus,
    Payment,
    PaymentEvent,
    PaymentStatus,
    User,
)
from app.providers.payment import payment_provider
from app.services.audit import append_audit
from app.services.idempotency import begin_idempotent
from app.services.lifecycle import (
    get_customer_booking,
    get_operator_booking,
    transition_booking,
)

router = APIRouter(prefix="/api/v1")


def kyc_response(case: KycCase) -> KycCaseResponse:
    return KycCaseResponse(
        id=case.id,
        status=case.status,
        country_code=case.country_code,
        service_type=case.service_type,
        provider=case.provider,
        reason=case.reason,
        verified_at=case.verified_at,
        expires_at=case.expires_at,
    )


@router.post("/kyc/cases", response_model=KycCaseResponse, status_code=201)
def create_kyc_case(
    payload: KycCaseCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KycCaseResponse:
    active = db.scalar(
        select(KycCase).where(
            KycCase.customer_id == user.id,
            KycCase.status.in_(["PENDING", "SUBMITTED", "UNDER_REVIEW", "VERIFIED"]),
        ).order_by(KycCase.created_at.desc())
    )
    if active is not None:
        return kyc_response(active)
    now = datetime.now(UTC)
    case = KycCase(
        id=uuid4(),
        customer_id=user.id,
        country_code=payload.country_code.upper(),
        service_type=payload.service_type.upper(),
        status="PENDING",
        created_at=now,
        updated_at=now,
    )
    db.add(case)
    db.commit()
    return kyc_response(case)


@router.get("/kyc/cases/me", response_model=list[KycCaseResponse])
def my_kyc_cases(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KycCaseResponse]:
    cases = db.scalars(
        select(KycCase)
        .where(KycCase.customer_id == user.id)
        .order_by(KycCase.created_at.desc())
    ).all()
    return [kyc_response(item) for item in cases]


@router.post("/admin/kyc/{case_id}/review", response_model=KycCaseResponse)
def review_kyc(
    case_id: UUID,
    payload: KycReviewRequest,
    request: Request,
    reviewer: User = Depends(require_permissions("kyc:approve")),
    db: Session = Depends(get_db),
) -> KycCaseResponse:
    case = db.get(KycCase, case_id)
    if case is None:
        raise NotFoundError("KYC case not found")
    before = {"status": case.status, "reason": case.reason}
    case.status = payload.decision
    case.reason = payload.reason
    case.reviewer_user_id = reviewer.id
    case.updated_at = datetime.now(UTC)
    case.verified_at = datetime.now(UTC) if payload.decision == "VERIFIED" else None
    case.expires_at = payload.expires_at if payload.decision == "VERIFIED" else None
    append_audit(
        db,
        actor_user_id=reviewer.id,
        action="kyc:review",
        entity="kyc_case",
        entity_id=str(case.id),
        request_id=getattr(request.state, "request_id", None),
        before_state=before,
        after_state={"status": case.status, "reason": case.reason},
    )
    db.commit()
    return kyc_response(case)


@router.post(
    "/bookings/{booking_id}/payments",
    response_model=PaymentInitiateResponse,
    status_code=201,
)
def initiate_payment(
    booking_id: UUID,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentInitiateResponse:
    try:
        booking = get_customer_booking(db, booking_id, user.id)
        idem = begin_idempotent(
            db,
            f"payment-initiate:{booking.id}",
            idempotency_key,
            {"booking_id": str(booking.id), "amount": str(booking.total_amount)},
        )
        if idem.response_body:
            return PaymentInitiateResponse.model_validate(idem.response_body)

        existing = db.scalar(
            select(Payment).where(
                Payment.booking_id == booking.id,
                Payment.status.in_([
                    PaymentStatus.PENDING,
                    PaymentStatus.AUTHORIZED,
                    PaymentStatus.CAPTURED,
                ]),
            )
        )
        if existing:
            raise ConflictError("PAYMENT_ALREADY_ACTIVE", "An active payment already exists")

        checkout = payment_provider().create_checkout(
            booking.id,
            booking.total_amount,
            booking.currency,
        )
        now = datetime.now(UTC)
        payment = Payment(
            id=uuid4(),
            booking_id=booking.id,
            customer_id=user.id,
            provider=checkout.provider,
            provider_transaction_id=checkout.external_reference,
            amount=booking.total_amount,
            currency=booking.currency,
            status=PaymentStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        db.add(payment)
        if booking.deposit_amount > 0 and db.scalar(
            select(Deposit.id).where(Deposit.booking_id == booking.id)
        ) is None:
            db.add(
                Deposit(
                    id=uuid4(),
                    booking_id=booking.id,
                    customer_id=user.id,
                    amount=booking.deposit_amount,
                    currency=booking.currency,
                    status="PENDING",
                    created_at=now,
                    updated_at=now,
                )
            )
        response = PaymentInitiateResponse(
            payment_id=payment.id,
            provider=checkout.provider,
            provider_reference=checkout.external_reference,
            status=checkout.status,
        )
        idem.response_code = 201
        idem.response_body = response.model_dump(mode="json")
        append_audit(
            db,
            actor_user_id=user.id,
            action="payment:initiate",
            entity="payment",
            entity_id=str(payment.id),
            request_id=getattr(request.state, "request_id", None),
            after_state={"booking_id": str(booking.id), "status": "PENDING"},
        )
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise


@router.post("/payments/webhooks/sandbox")
async def sandbox_payment_webhook(
    event: SandboxWebhookEvent,
    request: Request,
    signature: str = Header(alias="X-Payment-Signature"),
    db: Session = Depends(get_db),
) -> dict:
    raw = await request.body()
    provider = payment_provider()
    if provider.name != "sandbox":
        raise HTTPException(status_code=404, detail="Webhook provider not enabled")
    if not provider.verify_webhook(raw, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    if db.scalar(
        select(PaymentEvent.id).where(
            PaymentEvent.provider == provider.name,
            PaymentEvent.provider_event_id == event.event_id,
        )
    ):
        return {"success": True, "duplicate": True}

    payment = db.scalar(
        select(Payment).where(
            Payment.provider == provider.name,
            Payment.provider_transaction_id == event.transaction_id,
        )
    )
    if payment is None:
        raise NotFoundError("Payment transaction not found")

    allowed = {
        "PENDING": PaymentStatus.PENDING,
        "AUTHORIZED": PaymentStatus.AUTHORIZED,
        "CAPTURED": PaymentStatus.CAPTURED,
        "FAILED": PaymentStatus.FAILED,
    }
    payment.status = allowed[event.status]
    payment.updated_at = datetime.now(UTC)
    db.add(
        PaymentEvent(
            id=uuid4(),
            provider=provider.name,
            provider_event_id=event.event_id,
            payload_hash=hashlib.sha256(raw).hexdigest(),
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    return {"success": True, "duplicate": False}


@router.get("/bookings/{booking_id}/deposit", response_model=DepositResponse)
def get_deposit(
    booking_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DepositResponse:
    get_customer_booking(db, booking_id, user.id)
    deposit = db.scalar(select(Deposit).where(Deposit.booking_id == booking_id))
    if deposit is None:
        raise NotFoundError("Deposit not found")
    return DepositResponse(
        id=deposit.id,
        booking_id=deposit.booking_id,
        amount=deposit.amount,
        currency=deposit.currency,
        status=deposit.status,
    )


OPERATOR_TRANSITIONS = {
    BookingStatus.READY_FOR_PICKUP,
    BookingStatus.RENTAL_ACTIVE,
    BookingStatus.RETURN_PENDING,
    BookingStatus.VEHICLE_RETURNED,
}


@router.post("/operator/bookings/{booking_id}/transition")
def operator_transition(
    booking_id: UUID,
    payload: BookingTransitionRequest,
    request: Request,
    user: User = Depends(require_permissions("booking:update")),
    db: Session = Depends(get_db),
) -> dict:
    booking = get_operator_booking(db, booking_id, user)
    try:
        target = BookingStatus(payload.target_status)
    except ValueError as exc:
        raise ConflictError("INVALID_BOOKING_STATUS", "Unknown booking status") from exc
    if target not in OPERATOR_TRANSITIONS:
        raise ConflictError(
            "TRANSITION_REQUIRES_SPECIAL_WORKFLOW",
            "Use the dedicated KYC, payment, handover, inspection or finance workflow",
        )
    transition_booking(
        db,
        booking,
        target,
        user.id,
        getattr(request.state, "request_id", None),
    )
    db.commit()
    return {"booking_id": str(booking.id), "status": booking.status.value}


@router.post(
    "/operator/bookings/{booking_id}/handover",
    response_model=HandoverResponse,
    status_code=201,
)
def create_handover(
    booking_id: UUID,
    payload: HandoverCreateRequest,
    request: Request,
    user: User = Depends(require_permissions("handover:create")),
    db: Session = Depends(get_db),
) -> HandoverResponse:
    booking = get_operator_booking(db, booking_id, user)
    if booking.status != BookingStatus.READY_FOR_PICKUP:
        raise ConflictError("BOOKING_NOT_READY", "Booking is not ready for handover")
    if db.scalar(select(HandoverRecord.id).where(HandoverRecord.booking_id == booking.id)):
        raise ConflictError("HANDOVER_ALREADY_EXISTS", "Handover record is immutable")
    now = datetime.now(UTC)
    record = HandoverRecord(
        id=uuid4(),
        booking_id=booking.id,
        odometer=payload.odometer,
        fuel_level_percent=payload.fuel_level_percent,
        condition=payload.condition,
        accessories=payload.accessories,
        acknowledgement_method=payload.acknowledgement_method,
        acknowledged_by_user_id=payload.acknowledged_by_user_id,
        created_by_user_id=user.id,
        created_at=now,
    )
    db.add(record)
    transition_booking(
        db,
        booking,
        BookingStatus.VEHICLE_HANDED_OVER,
        user.id,
        getattr(request.state, "request_id", None),
    )
    append_audit(
        db,
        actor_user_id=user.id,
        action="handover:create",
        entity="handover",
        entity_id=str(record.id),
        request_id=getattr(request.state, "request_id", None),
        after_state={"booking_id": str(booking.id)},
    )
    db.commit()
    return HandoverResponse(
        id=record.id,
        booking_id=record.booking_id,
        odometer=record.odometer,
        fuel_level_percent=record.fuel_level_percent,
        created_at=record.created_at,
    )


@router.post(
    "/operator/bookings/{booking_id}/inspection",
    response_model=InspectionResponse,
    status_code=201,
)
def create_inspection(
    booking_id: UUID,
    payload: InspectionCreateRequest,
    request: Request,
    user: User = Depends(require_permissions("inspection:create")),
    db: Session = Depends(get_db),
) -> InspectionResponse:
    booking = get_operator_booking(db, booking_id, user)
    if booking.status != BookingStatus.VEHICLE_RETURNED:
        raise ConflictError("VEHICLE_NOT_RETURNED", "Vehicle must be returned before inspection")
    if db.scalar(select(InspectionRecord.id).where(InspectionRecord.booking_id == booking.id)):
        raise ConflictError("INSPECTION_ALREADY_EXISTS", "Inspection record is immutable")
    handover = db.scalar(
        select(HandoverRecord).where(HandoverRecord.booking_id == booking.id)
    )
    if handover is None:
        raise ConflictError("HANDOVER_MISSING", "Cannot inspect without a handover record")
    if payload.odometer < handover.odometer:
        raise ConflictError("ODOMETER_REGRESSION", "Return odometer cannot be below handover odometer")

    now = datetime.now(UTC)
    record = InspectionRecord(
        id=uuid4(),
        booking_id=booking.id,
        odometer=payload.odometer,
        fuel_level_percent=payload.fuel_level_percent,
        condition=payload.condition,
        accessories=payload.accessories,
        additional_km=payload.additional_km,
        late_minutes=payload.late_minutes,
        created_by_user_id=user.id,
        created_at=now,
    )
    db.add(record)
    transition_booking(
        db,
        booking,
        BookingStatus.INSPECTION_PENDING,
        user.id,
        getattr(request.state, "request_id", None),
    )
    db.commit()
    return InspectionResponse(
        id=record.id,
        booking_id=record.booking_id,
        odometer=record.odometer,
        fuel_level_percent=record.fuel_level_percent,
        additional_km=record.additional_km,
        late_minutes=record.late_minutes,
        created_at=record.created_at,
    )


@router.post(
    "/operator/bookings/{booking_id}/damages",
    response_model=DamageResponse,
    status_code=201,
)
def create_damage(
    booking_id: UUID,
    payload: DamageCreateRequest,
    user: User = Depends(require_permissions("damage:create")),
    db: Session = Depends(get_db),
) -> DamageResponse:
    booking = get_operator_booking(db, booking_id, user)
    if db.scalar(
        select(InspectionRecord.id).where(InspectionRecord.booking_id == booking.id)
    ) is None:
        raise ConflictError("INSPECTION_REQUIRED", "Complete return inspection first")
    now = datetime.now(UTC)
    damage = DamageRecord(
        id=uuid4(),
        booking_id=booking.id,
        vehicle_id=booking.vehicle_id,
        location=payload.location,
        description=payload.description,
        severity=payload.severity,
        estimated_cost=payload.estimated_cost,
        status="REPORTED",
        created_at=now,
        updated_at=now,
    )
    db.add(damage)
    db.commit()
    return DamageResponse(
        id=damage.id,
        booking_id=damage.booking_id,
        status=damage.status,
        severity=damage.severity,
        estimated_cost=damage.estimated_cost,
    )


@router.post(
    "/bookings/{booking_id}/review",
    response_model=ReviewResponse,
    status_code=201,
)
def create_review(
    booking_id: UUID,
    payload: ReviewCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    booking = get_customer_booking(db, booking_id, user.id)
    if booking.status != BookingStatus.COMPLETED:
        raise ConflictError("BOOKING_NOT_COMPLETED", "Review is available after completion")
    if db.scalar(
        select(Review.id).where(
            Review.booking_id == booking.id,
            Review.customer_id == user.id,
        )
    ):
        raise ConflictError("REVIEW_ALREADY_EXISTS", "Booking has already been reviewed")
    now = datetime.now(UTC)
    review = Review(
        id=uuid4(),
        booking_id=booking.id,
        customer_id=user.id,
        overall_rating=payload.overall_rating,
        vehicle_rating=payload.vehicle_rating,
        operator_rating=payload.operator_rating,
        driver_rating=payload.driver_rating,
        comment=payload.comment,
        moderation_status="VISIBLE",
        created_at=now,
        updated_at=now,
    )
    db.add(review)
    db.commit()
    return ReviewResponse(
        id=review.id,
        booking_id=review.booking_id,
        overall_rating=review.overall_rating,
        moderation_status=review.moderation_status,
    )


@router.post("/support/tickets", response_model=SupportTicketResponse, status_code=201)
def create_support_ticket(
    payload: SupportTicketCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SupportTicketResponse:
    if payload.booking_id is not None:
        get_customer_booking(db, payload.booking_id, user.id)
    now = datetime.now(UTC)
    ticket = SupportTicket(
        id=uuid4(),
        customer_id=user.id,
        booking_id=payload.booking_id,
        category=payload.category,
        priority=payload.priority,
        subject=payload.subject,
        status="OPEN",
        created_at=now,
        updated_at=now,
    )
    db.add(ticket)
    db.commit()
    return SupportTicketResponse(
        id=ticket.id,
        booking_id=ticket.booking_id,
        category=ticket.category,
        priority=ticket.priority,
        subject=ticket.subject,
        status=ticket.status,
    )
