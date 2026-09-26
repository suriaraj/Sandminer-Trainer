from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Operator, OperatorUser, User, VehicleCategory
from app.operations_schemas import OperatorResponse

router = APIRouter(prefix="/api/v1")


@router.get("/vehicle-categories")
def vehicle_categories(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(
        select(VehicleCategory)
        .where(VehicleCategory.active.is_(True))
        .order_by(VehicleCategory.name)
    ).all()
    return [{"id": str(item.id), "code": item.code, "name": item.name} for item in rows]


@router.get("/operator/profile", response_model=list[OperatorResponse])
def operator_profiles(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OperatorResponse]:
    rows = db.scalars(
        select(Operator)
        .join(OperatorUser, OperatorUser.operator_id == Operator.id)
        .where(OperatorUser.user_id == user.id)
        .order_by(Operator.created_at.desc())
    ).all()
    return [
        OperatorResponse(
            id=item.id,
            legal_name=item.legal_name,
            business_name=item.business_name,
            status=item.status,
        ) for item in rows
    ]
