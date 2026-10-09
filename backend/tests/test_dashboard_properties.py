import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException


class DashboardPropertyEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_endpoint_uses_authenticated_tenant_only(self):
        from app.api.v1.dashboard import get_dashboard_properties

        properties = [{"id": "prop-001", "name": "Beach House Alpha"}]
        with patch(
            "app.api.v1.dashboard.get_tenant_properties",
            new=AsyncMock(return_value=properties),
        ) as query:
            response = await get_dashboard_properties(
                current_user=SimpleNamespace(tenant_id="tenant-a")
            )

        self.assertEqual(response, {"properties": properties})
        query.assert_awaited_once_with("tenant-a")

    async def test_endpoint_rejects_missing_authenticated_tenant(self):
        from app.api.v1.dashboard import get_dashboard_properties

        with self.assertRaises(HTTPException) as caught:
            await get_dashboard_properties(current_user=SimpleNamespace(tenant_id=None))

        self.assertEqual(caught.exception.status_code, 403)


class TenantPropertyDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        from app.core.database_pool import db_pool

        if db_pool.engine is not None:
            await db_pool.close()
        db_pool.engine = None
        db_pool.session_factory = None

    @unittest.skipUnless(os.getenv("DATABASE_URL"), "run inside the Docker backend with DATABASE_URL")
    async def test_seed_property_lists_are_tenant_scoped(self):
        from app.services.properties import get_tenant_properties

        tenant_a = await get_tenant_properties("tenant-a")
        tenant_b = await get_tenant_properties("tenant-b")

        self.assertEqual(
            {(item["id"], item["name"]) for item in tenant_a},
            {
                ("prop-001", "Beach House Alpha"),
                ("prop-002", "City Apartment Downtown"),
                ("prop-003", "Country Villa Estate"),
            },
        )
        self.assertEqual(
            {(item["id"], item["name"]) for item in tenant_b},
            {
                ("prop-001", "Mountain Lodge Beta"),
                ("prop-004", "Lakeside Cottage"),
                ("prop-005", "Urban Loft Modern"),
            },
        )


if __name__ == "__main__":
    unittest.main()
