from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AuthorizationError, ConflictError, NotFoundError
from app.core.security import get_current_user, require_permissions
from app.lifecycle_models import KycCase
from app.marketplace_models import AvailabilityPolicy
from app.models import (
    Booking,
    BookingStatus,
    Operator,
    OperatorUser,
    Payment,
    PaymentStatus,
    PricingPackage,
    Role,
    User,
    UserRole,
    Vehicle,
    VehicleCategory,
)
from app.operations_schemas import (
    AdminKpiResponse,
    AvailabilityPolicyRequest,
    AvailabilityPolicyResponse,
    OperatorCreateRequest,
    OperatorResponse,
    OperatorStatusRequest,
    PricingPackageCreateRequest,
    PricingPackageResponse,
    VehicleCreateRequest,
    VehicleResponse,
    VehicleStatusRequest,
)
from app.schemas import BookingResponse
from app.services.audit import append_audit

router = APIRouter(prefix="/api/v1")


def owns_operator(db: Session, user_id: UUID, operator_id: UUID) -> bool:
    return bool(
        db.scalar(
            select(func.count())
            .select_from(OperatorUser)
            .where(
                OperatorUser.user_id == user_id,
                OperatorUser.operator_id == operator_id,
            )
        )
    )


def booking_response(booking: Booking) -> BookingResponse:
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


@router.get("/bookings", response_model=list[BookingResponse])
def list_customer_bookings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BookingResponse]:
    bookings = db.scalars(
        select(Booking)
        .where(Booking.customer_id == user.id)
        .order_by(Booking.created_at.desc())
        .limit(200)
    ).all()
    return [booking_response(item) for item in bookings]


@router.post("/operators", response_model=OperatorResponse, status_code=201)
def create_operator(
    payload: OperatorCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OperatorResponse:
    now = datetime.now(UTC)
    operator = Operator(
        id=uuid4(),
        legal_name=payload.legal_name.strip(),
        business_name=payload.business_name.strip(),
        status="REGISTERED",
        created_at=now,
        updated_at=now,
    )
    db.add(operator)
    db.flush()
    db.add(OperatorUser(operator_id=operator.id, user_id=user.id))

    role = db.scalar(select(Role).where(Role.code == "OPERATOR_OWNER"))
    if role is None:
        raise ConflictError("RBAC_NOT_INITIALIZED", "OPERATOR_OWNER role is missing")
    if db.get(UserRole, (user.id, role.id)) is None:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return OperatorResponse(
        id=operator.id,
        legal_name=operator.legal_name,
        business_name=operator.business_name,
        status=operator.status,
    )


@router.get("/operator/vehicles", response_model=list[VehicleResponse])
def list_operator_vehicles(
    user: User = Depends(require_permissions("vehicle:read")),
    db: Session = Depends(get_db),
) -> list[VehicleResponse]:
    operator_ids = select(OperatorUser.operator_id).where(OperatorUser.user_id == user.id)
    rows = db.scalars(
        select(Vehicle)
        .where(Vehicle.operator_id.in_(operator_ids))
        .order_by(Vehicle.created_at.desc())
        .limit(500)
    ).all()
    return [
        VehicleResponse(
            id=v.id,
            operator_id=v.operator_id,
            category_id=v.category_id,
            registration_number=v.registration_number,
            brand=v.brand,
            model=v.model,
            variant=v.variant,
            city=v.city,
            timezone=v.timezone,
            status=v.status,
            fuel=v.fuel,
            transmission=v.transmission,
            seats=v.seats,
        )
        for v in rows
    ]


@router.post("/operator/vehicles", response_model=VehicleResponse, status_code=201)
def create_vehicle(
    payload: VehicleCreateRequest,
    user: User = Depends(require_permissions("vehicle:create")),
    db: Session = Depends(get_db),
) -> VehicleResponse:
    if not owns_operator(db, user.id, payload.operator_id):
        raise AuthorizationError("Operator does not belong to this user")
    category = db.get(VehicleCategory, payload.category_id)
    if category is None or not category.active:
        raise NotFoundError("Vehicle category not found")
    if db.scalar(
        select(Vehicle.id).where(
            Vehicle.registration_number == payload.registration_number.upper()
        )
    ):
        raise ConflictError("VEHICLE_ALREADY_EXISTS", "Registration number already exists")
    now = datetime.now(UTC)
    vehicle = Vehicle(
        id=uuid4(),
        operator_id=payload.operator_id,
        category_id=payload.category_id,
        registration_number=payload.registration_number.upper(),
        brand=payload.brand.strip(),
        model=payload.model.strip(),
        variant=payload.variant,
        city=payload.city.strip(),
        timezone=payload.timezone,
        status="INACTIVE",
        fuel=payload.fuel,
        transmission=payload.transmission,
        seats=payload.seats,
        created_at=now,
        updated_at=now,
    )
    db.add(vehicle)
    db.commit()
    return VehicleResponse(
        id=vehicle.id,
        operator_id=vehicle.operator_id,
        category_id=vehicle.category_id,
        registration_number=vehicle.registration_number,
        brand=vehicle.brand,
        model=vehicle.model,
        variant=vehicle.variant,
        city=vehicle.city,
        timezone=vehicle.timezone,
        status=vehicle.status,
        fuel=vehicle.fuel,
        transmission=vehicle.transmission,
        seats=vehicle.seats,
    )


@router.post(
    "/operator/packages",
    response_model=PricingPackageResponse,
    status_code=201,
)
def create_pricing_package(
    payload: PricingPackageCreateRequest,
    user: User = Depends(require_permissions("pricing:update")),
    db: Session = Depends(get_db),
) -> PricingPackageResponse:
    if not owns_operator(db, user.id, payload.operator_id):
        raise AuthorizationError("Operator does not belong to this user")
    now = datetime.now(UTC)
    item = PricingPackage(
        id=uuid4(),
        operator_id=payload.operator_id,
        name=payload.name,
        service_type=payload.service_type,
        duration_minutes=payload.duration_minutes,
        included_km=payload.included_km,
        base_price=payload.base_price,
        tax_rate=payload.tax_rate,
        deposit=payload.deposit,
        currency=payload.currency.upper(),
        active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    db.commit()
    return PricingPackageResponse.model_validate(item, from_attributes=True)


@router.get(
    "/vehicles/{vehicle_id}/packages",
    response_model=list[PricingPackageResponse],
)
def list_vehicle_packages(
    vehicle_id: UUID,
    service_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[PricingPackageResponse]:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.status != "AVAILABLE":
        raise NotFoundError("Vehicle not found")
    packages = db.scalars(
        select(PricingPackage).where(
            PricingPackage.operator_id == vehicle.operator_id,
            PricingPackage.active.is_(True),
            (PricingPackage.service_type == service_type) if service_type else True,
        )
    ).all()
    return [
        PricingPackageResponse.model_validate(item, from_attributes=True)
        for item in packages
    ]


@router.get("/operator/bookings", response_model=list[BookingResponse])
def list_operator_bookings(
    user: User = Depends(require_permissions("booking:read")),
    db: Session = Depends(get_db),
) -> list[BookingResponse]:
    operator_ids = select(OperatorUser.operator_id).where(OperatorUser.user_id == user.id)
    bookings = db.scalars(
        select(Booking)
        .where(Booking.operator_id.in_(operator_ids))
        .order_by(Booking.created_at.desc())
        .limit(500)
    ).all()
    return [booking_response(item) for item in bookings]


@router.put(
    "/operator/{operator_id}/availability-policy",
    response_model=AvailabilityPolicyResponse,
)
def update_operator_availability_policy(
    operator_id: UUID,
    payload: AvailabilityPolicyRequest,
    user: User = Depends(require_permissions("pricing:update")),
    db: Session = Depends(get_db),
) -> AvailabilityPolicyResponse:
    if not owns_operator(db, user.id, operator_id):
        raise AuthorizationError("Operator does not belong to this user")
    item = db.scalar(
        select(AvailabilityPolicy).where(
            AvailabilityPolicy.operator_id == operator_id
        )
    )
    if item is None:
        item = AvailabilityPolicy(
            id=uuid4(),
            scope_key=f"OPERATOR:{operator_id}",
            operator_id=operator_id,
            pre_buffer_minutes=payload.pre_buffer_minutes,
            post_buffer_minutes=payload.post_buffer_minutes,
            updated_at=datetime.now(UTC),
        )
        db.add(item)
    else:
        item.pre_buffer_minutes = payload.pre_buffer_minutes
        item.post_buffer_minutes = payload.post_buffer_minutes
        item.updated_at = datetime.now(UTC)
    db.commit()
    return AvailabilityPolicyResponse(
        operator_id=operator_id,
        pre_buffer_minutes=item.pre_buffer_minutes,
        post_buffer_minutes=item.post_buffer_minutes,
    )


@router.post("/admin/operators/{operator_id}/status", response_model=OperatorResponse)
def admin_operator_status(
    operator_id: UUID,
    payload: OperatorStatusRequest,
    request: Request,
    admin: User = Depends(require_permissions("operator:approve")),
    db: Session = Depends(get_db),
) -> OperatorResponse:
    operator = db.get(Operator, operator_id)
    if operator is None:
        raise NotFoundError("Operator not found")
    before = {"status": operator.status}
    operator.status = payload.status
    operator.updated_at = datetime.now(UTC)
    append_audit(
        db,
        actor_user_id=admin.id,
        action="operator:status",
        entity="operator",
        entity_id=str(operator.id),
        request_id=getattr(request.state, "request_id", None),
        before_state=before,
        after_state={"status": operator.status},
    )
    db.commit()
    return OperatorResponse(
        id=operator.id,
        legal_name=operator.legal_name,
        business_name=operator.business_name,
        status=operator.status,
    )


@router.post("/admin/vehicles/{vehicle_id}/status", response_model=VehicleResponse)
def admin_vehicle_status(
    vehicle_id: UUID,
    payload: VehicleStatusRequest,
    request: Request,
    admin: User = Depends(require_permissions("operator:approve")),
    db: Session = Depends(get_db),
) -> VehicleResponse:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise NotFoundError("Vehicle not found")
    before = {"status": vehicle.status}
    vehicle.status = payload.status
    vehicle.updated_at = datetime.now(UTC)
    append_audit(
        db,
        actor_user_id=admin.id,
        action="vehicle:status",
        entity="vehicle",
        entity_id=str(vehicle.id),
        request_id=getattr(request.state, "request_id", None),
        before_state=before,
        after_state={"status": vehicle.status},
    )
    db.commit()
    return VehicleResponse(
        id=vehicle.id,
        operator_id=vehicle.operator_id,
        category_id=vehicle.category_id,
        registration_number=vehicle.registration_number,
        brand=vehicle.brand,
        model=vehicle.model,
        variant=vehicle.variant,
        city=vehicle.city,
        timezone=vehicle.timezone,
        status=vehicle.status,
        fuel=vehicle.fuel,
        transmission=vehicle.transmission,
        seats=vehicle.seats,
    )


@router.get("/admin/kpis", response_model=AdminKpiResponse)
def admin_kpis(
    _: User = Depends(require_permissions("admin:users")),
    db: Session = Depends(get_db),
) -> AdminKpiResponse:
    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    total_operators = db.scalar(select(func.count()).select_from(Operator)) or 0
    total_vehicles = db.scalar(select(func.count()).select_from(Vehicle)) or 0
    available_vehicles = db.scalar(
        select(func.count()).select_from(Vehicle).where(Vehicle.status == "AVAILABLE")
    ) or 0
    total_bookings = db.scalar(select(func.count()).select_from(Booking)) or 0
    active_rentals = db.scalar(
        select(func.count())
        .select_from(Booking)
        .where(Booking.status == BookingStatus.RENTAL_ACTIVE)
    ) or 0
    captured_revenue = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.CAPTURED
        )
    )
    pending_kyc = db.scalar(
        select(func.count())
        .select_from(KycCase)
        .where(KycCase.status.in_(["SUBMITTED", "UNDER_REVIEW"]))
    ) or 0
    return AdminKpiResponse(
        total_users=total_users,
        total_operators=total_operators,
        total_vehicles=total_vehicles,
        available_vehicles=available_vehicles,
        total_bookings=total_bookings,
        active_rentals=active_rentals,
        captured_revenue=Decimal(captured_revenue or 0),
        pending_kyc=pending_kyc,
    )
