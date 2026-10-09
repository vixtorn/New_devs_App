import os
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException


class MemoryRedis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def setex(self, key, ttl, value):
        self.values[key] = value


class RevenueCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_property_id_is_cached_separately_for_each_tenant(self):
        from app.services.cache import get_revenue_summary

        cache = MemoryRedis()
        async def calculate(property_id, tenant_id, month, year):
            return {
                "property_id": property_id,
                "tenant_id": tenant_id,
                "total": "2250.000" if tenant_id == "tenant-a" else "0.000",
                "currency": "USD",
                "count": 4 if tenant_id == "tenant-a" else 0,
            }

        with patch("app.services.cache.redis_client", cache), patch(
            "app.services.reservations.calculate_monthly_summary", new=AsyncMock(side_effect=calculate)
        ) as calculator:
            sunset = await get_revenue_summary("prop-001", "tenant-a", 3, 2024)
            ocean = await get_revenue_summary("prop-001", "tenant-b", 3, 2024)

        self.assertEqual(sunset["tenant_id"], "tenant-a")
        self.assertEqual(ocean["tenant_id"], "tenant-b")
        self.assertEqual(ocean["total"], "0.000")
        self.assertEqual(calculator.await_count, 2)


class RevenueDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        from app.core.database_pool import db_pool

        if db_pool.engine is not None:
            await db_pool.close()
        db_pool.engine = None
        db_pool.session_factory = None

    @unittest.skipUnless(os.getenv("DATABASE_URL"), "run inside the Docker backend with DATABASE_URL")
    async def test_march_report_uses_property_timezone_and_tenant_scope(self):
        from app.services.reservations import calculate_monthly_revenue

        sunset = await calculate_monthly_revenue("prop-001", "tenant-a", 3, 2024)
        ocean = await calculate_monthly_revenue("prop-001", "tenant-b", 3, 2024)

        # The 2024-02-29 23:30 UTC reservation is March 1 in the property's Paris timezone.
        self.assertEqual(sunset, Decimal("2250.000"))
        self.assertEqual(ocean, Decimal("0"))

    @unittest.skipUnless(os.getenv("DATABASE_URL"), "run inside the Docker backend with DATABASE_URL")
    async def test_march_report_sums_exact_numeric_amounts(self):
        from app.services.reservations import calculate_monthly_revenue

        total = await calculate_monthly_revenue("prop-002", "tenant-a", 3, 2024)
        self.assertEqual(total, Decimal("4975.50"))

    async def test_database_failure_is_raised_instead_of_becoming_fake_revenue(self):
        from app.services.reservations import calculate_total_revenue

        import app.core.database_pool as database_pool

        with patch.object(database_pool, "db_pool") as db_pool:
            db_pool.session_factory = None
            db_pool.initialize = AsyncMock(side_effect=RuntimeError("database unavailable"))
            with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                await calculate_total_revenue("prop-001", "tenant-a")


class DashboardEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_response_keeps_money_as_exact_two_decimal_string(self):
        from app.api.v1.dashboard import get_dashboard_summary

        with patch(
            "app.api.v1.dashboard.get_revenue_summary",
            new=AsyncMock(return_value={
                "property_id": "prop-001",
                "tenant_id": "tenant-a",
                "total": "1000.005",
                "currency": "USD",
                "count": 3,
            }),
        ):
            response = await get_dashboard_summary(
                property_id="prop-001",
                month=3,
                year=2024,
                current_user=SimpleNamespace(tenant_id="tenant-a"),
            )

        self.assertEqual(response["total_revenue"], "1000.01")
        self.assertIsInstance(response["total_revenue"], str)

    async def test_dashboard_rejects_users_without_authenticated_tenant(self):
        from app.api.v1.dashboard import get_dashboard_summary

        with self.assertRaises(HTTPException) as caught:
            await get_dashboard_summary(
                property_id="prop-001",
                month=3,
                year=2024,
                current_user=SimpleNamespace(tenant_id=None),
            )

        self.assertEqual(caught.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
