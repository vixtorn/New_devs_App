from typing import Any, Dict, List

from sqlalchemy import text


async def get_tenant_properties(tenant_id: str) -> List[Dict[str, Any]]:
    """Fetch dashboard property options for one authenticated tenant."""
    if not tenant_id:
        raise ValueError("tenant_id is required")

    from app.core.database_pool import db_pool

    if db_pool.session_factory is None:
        await db_pool.initialize()
    if db_pool.session_factory is None:
        raise RuntimeError("Database pool is not available")

    async with db_pool.get_session() as session:
        result = await session.execute(
            text("SELECT id, name FROM properties WHERE tenant_id = :tenant_id ORDER BY name, id"),
            {"tenant_id": tenant_id},
        )
        return [dict(row) for row in result.mappings().all()]
