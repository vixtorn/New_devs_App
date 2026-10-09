from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.cache import get_revenue_summary
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:

    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Authenticated tenant is required")

    if (month is None) != (year is None):
        raise HTTPException(status_code=422, detail="month and year must be provided together")
    if month is None or year is None:
        now = datetime.now(timezone.utc)
        month, year = now.month, now.year

    revenue_data = await get_revenue_summary(property_id, tenant_id, month, year)
    total_revenue = Decimal(str(revenue_data["total"])).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    
    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": format(total_revenue, ".2f"),
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }
