from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_models import AuthSession
from app.auth_schemas import RefreshRequest, SessionResponse
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError
from app.core.security import get_current_user, hash_password, verify_password
from app.marketplace_models import RentalConfiguration
from app.models import Booking, PricingPackage, Quote, Role, User, UserRole, Vehicle
from app.schemas import (
    BookingCreateRequest,
    BookingResponse,
    LoginRequest,
    QuoteCreateRequest,
    QuoteResponse,
    RegisterRequest,
    TokenResponse,
    VehicleSearchItem,
)
from app.services.audit import append_audit
from app.services.auth_sessions import (
    issue_session,
    revoke_all_sessions,
    revoke_session,
    rotate_session,
)
from app.services.availability import is_vehicle_available, search_available_vehicles
from app.services.booking import create_booking_from_quote
from app.services.idempotency import begin_idempotent
from app.services.pricing import build_price

router = APIRouter(prefix="/api/v1")


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
def register(
    payload: RegisterRequest,
    device_label: str | None = Header(default=None, alias="X-Device-Label"),
    db: Session = Depends(get_db),
) -> TokenResponse:
    email = payload.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise ConflictError(
            "EMAIL_ALREADY_REGISTERED",
            "An account already exists for this email",
        )

    now = datetime.now(UTC)
    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.flush()

    customer_role = db.scalar(select(Role).where(Role.code == "CUSTOMER"))
    if customer_role is None:
        raise ConflictError(
            "RBAC_NOT_INITIALIZED",
            "Database role seed is missing; apply all migrations before registration",
        )
    db.add(UserRole(user_id=user.id, role_id=customer_role.id))

    access, refresh, _ = issue_session(db, user.id, device_label)
    db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    device_label: str | None = Header(default=None, alias="X-Device-Label"),
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access, refresh, _ = issue_session(db, user.id, device_label)
    db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh_session(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    access, refresh, _ = rotate_session(db, payload.refresh_token)
    db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.get("/auth/sessions", response_model=list[SessionResponse])
def list_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SessionResponse]:
    sessions = db.scalars(
        select(AuthSession)
        .where(AuthSession.user_id == user.id)
        .order_by(AuthSession.created_at.desc())
    ).all()
    return [
        SessionResponse(
            id=item.id,
            device_label=item.device_label,
            created_at=item.created_at,
            last_used_at=item.last_used_at,
            expires_at=item.expires_at,
            revoked=item.revoked_at is not None,
        )
        for item in sessions
    ]


@router.delete("/auth/sessions/{session_id}", status_code=204)
def logout_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not revoke_session(db, user.id, session_id):
        raise NotFoundError("Session not found")
    db.commit()


@router.post("/auth/logout-all")
def logout_all_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    count = revoke_all_sessions(db, user.id)
    db.commit()
    return {"revoked_sessions": count}


@router.get("/vehicles/search", response_model=list[VehicleSearchItem])
def vehicle_search(
    city: str = Query(min_length=2, max_length=100),
    pickup_at: datetime = Query(),
    return_at: datetime = Query(),
    db: Session = Depends(get_db),
) -> list[VehicleSearchItem]:
    if pickup_at.tzinfo is None or return_at.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="pickup_at and return_at must include a timezone",
        )
    if return_at <= pickup_at:
        raise HTTPException(status_code=422, detail="return_at must be after pickup_at")

    vehicles = search_available_vehicles(db, city, pickup_at, return_at)
    return [
        VehicleSearchItem(
            id=vehicle.id,
            brand=vehicle.brand,
            model=vehicle.model,
            variant=vehicle.variant,
            city=vehicle.city,
            fuel=vehicle.fuel,
            transmission=vehicle.transmission,
            seats=vehicle.seats,
        )
        for vehicle in vehicles
    ]


@router.post("/quotes", response_model=QuoteResponse, status_code=201)
def create_quote(
    payload: QuoteCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuoteResponse:
    package = db.get(PricingPackage, payload.package_id)
    vehicle = db.get(Vehicle, payload.vehicle_id)

    if package is None or not package.active:
        raise NotFoundError("Rental package not found")
    if vehicle is None or vehicle.status != "AVAILABLE":
        raise ConflictError("VEHICLE_NOT_AVAILABLE", "Vehicle is not available")
    if package.operator_id != vehicle.operator_id:
        raise ConflictError(
            "PACKAGE_VEHICLE_MISMATCH",
            "Package is not valid for this vehicle",
        )
    if not is_vehicle_available(
        db,
        vehicle.id,
        payload.pickup_at,
        payload.return_at,
    ):
        raise ConflictError(
            "VEHICLE_NOT_AVAILABLE",
            "The selected vehicle is no longer available",
        )
    if payload.coupon_code:
        raise HTTPException(
            status_code=501,
            detail="Coupon engine is not enabled in this foundation",
        )

    price = build_price(
        base_price=package.base_price,
        deposit=package.deposit,
        tax_rate=package.tax_rate,
        discount=Decimal("0"),
        currency=package.currency,
    )
    now = datetime.now(UTC)
    quote = Quote(
        id=uuid4(),
        customer_id=user.id,
        vehicle_id=vehicle.id,
        package_id=package.id,
        pickup_at=payload.pickup_at,
        return_at=payload.return_at,
        pricing_version="base-v1",
        currency=price.currency,
        subtotal=price.subtotal,
        tax=price.tax,
        discount=price.discount,
        deposit=price.deposit,
        total=price.total,
        line_items=price.line_items,
        expires_at=now + timedelta(minutes=15),
        created_at=now,
        updated_at=now,
    )
    db.add(quote)
    db.add(
        RentalConfiguration(
            id=uuid4(),
            quote_id=quote.id,
            service_type=payload.service_type,
            pickup_location=payload.pickup_location,
            return_location=payload.return_location,
            booking_timezone=payload.booking_timezone,
            details={},
        )
    )
    db.commit()
    return QuoteResponse.model_validate(quote, from_attributes=True)


@router.post("/bookings", response_model=BookingResponse, status_code=201)
def create_booking(
    payload: BookingCreateRequest,
    request: Request,
    idempotency_key: str = Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=160,
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookingResponse:
    try:
        idem = begin_idempotent(
            db,
            f"booking:{user.id}",
            idempotency_key,
            payload.model_dump(mode="json"),
        )
        if idem.response_body is not None:
            return BookingResponse.model_validate(idem.response_body)

        quote = db.get(Quote, payload.quote_id)
        if quote is None:
            raise NotFoundError("Quote not found")

        booking = create_booking_from_quote(db, quote, user.id)
        append_audit(
            db,
            actor_user_id=user.id,
            action="booking:create",
            entity="booking",
            entity_id=str(booking.id),
            request_id=getattr(request.state, "request_id", None),
            after_state={
                "status": booking.status.value,
                "quote_id": str(quote.id),
            },
        )
        response = BookingResponse(
            id=booking.id,
            booking_number=booking.booking_number,
            vehicle_id=booking.vehicle_id,
            pickup_at=booking.pickup_at,
            return_at=booking.return_at,
            status=booking.status.value,
            currency=booking.currency,
            total_amount=booking.total_amount,
            deposit_amount=booking.deposit_amount,
        )
        idem.response_code = 201
        idem.response_body = response.model_dump(mode="json")
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookingResponse:
    booking = db.get(Booking, booking_id)
    if booking is None or booking.customer_id != user.id:
        raise NotFoundError("Booking not found")

    return BookingResponse(
        id=booking.id,
        booking_number=booking.booking_number,
        vehicle_id=booking.vehicle_id,
        pickup_at=booking.pickup_at,
        return_at=booking.return_at,
        status=booking.status.value,
        currency=booking.currency,
        total_amount=booking.total_amount,
        deposit_amount=booking.deposit_amount,
    )
