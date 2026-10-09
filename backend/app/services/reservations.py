from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _get_db_pool():
    from app.core.database_pool import db_pool

    if db_pool.session_factory is None:
        await db_pool.initialize()
    if db_pool.session_factory is None:
        raise RuntimeError("Database pool is not available")
    return db_pool


async def _fetch_revenue(
    property_id: str,
    tenant_id: str,
    *,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db_session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    if not tenant_id:
        raise ValueError("tenant_id is required for revenue queries")

    filters = ""
    parameters: Dict[str, Any] = {"property_id": property_id, "tenant_id": tenant_id}
    if start_date is not None and end_date is not None:
        filters = """
            AND r.check_in_date >= (CAST(:start_date AS TIMESTAMP) AT TIME ZONE p.timezone)
            AND r.check_in_date < (CAST(:end_date AS TIMESTAMP) AT TIME ZONE p.timezone)
        """
        parameters.update(start_date=start_date, end_date=end_date)

    query = text(f"""
        SELECT COALESCE(SUM(r.total_amount), 0) AS total_revenue,
               COUNT(r.id) AS reservation_count
        FROM reservations AS r
        JOIN properties AS p
          ON p.id = r.property_id AND p.tenant_id = r.tenant_id
        WHERE r.property_id = :property_id
          AND r.tenant_id = :tenant_id
          {filters}
    """)

    async def execute(session: AsyncSession) -> Dict[str, Any]:
        result = await session.execute(query, parameters)
        row = result.fetchone()
        amount = Decimal(str(row.total_revenue if row else 0))
        return {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "total": str(amount),
            "currency": "USD",
            "count": int(row.reservation_count if row else 0),
        }

    if db_session is not None:
        return await execute(db_session)

    pool = await _get_db_pool()
    async with pool.get_session() as session:
        return await execute(session)


async def calculate_monthly_summary(
    property_id: str,
    tenant_id: str,
    month: int,
    year: int,
    db_session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Return reservation revenue whose check-in falls in the property's local month."""
    if not 1 <= month <= 12:
        raise ValueError("month must be between 1 and 12")
    if year < 1:
        raise ValueError("year must be positive")

    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    return await _fetch_revenue(
        property_id,
        tenant_id,
        start_date=start_date,
        end_date=end_date,
        db_session=db_session,
    )


async def calculate_monthly_revenue(
    property_id: str,
    tenant_id: str,
    month: int,
    year: int,
    db_session: Optional[AsyncSession] = None,
) -> Decimal:
    """Calculate exact monthly revenue for one tenant and property."""
    summary = await calculate_monthly_summary(
        property_id, tenant_id, month, year, db_session=db_session
    )
    return Decimal(summary["total"])


async def calculate_total_revenue(
    property_id: str,
    tenant_id: str,
    db_session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Aggregate all reservation revenue for a tenant/property from PostgreSQL."""
    return await _fetch_revenue(property_id, tenant_id, db_session=db_session)
