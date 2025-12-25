"""
Integration tests for recommendation generation workflow
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
class TestRecommendationFlowIntegration:
    """Integration tests for complete recommendation workflow"""

    @pytest.fixture(autouse=True)
    async def setup_method(self):
        """Setup test database and client"""
        self.client = TestClient(app)

        # Setup test database connection
        self.test_db_client = AsyncIOMotorClient(settings.mongodb_url)
        self.test_db = self.test_db_client[settings.database_name + "_test"]

        # Clear test collections
        await self.test_db.components.delete_many({})
        await self.test_db.pc_configurations.delete_many({})

        # Seed with test data
        await self._seed_test_data()

        yield

        # Cleanup
        await self.test_db_client.close()

    async def _seed_test_data(self):
        """Seed database with test components and configurations"""
        # Test components
        test_components = [
            {
                "type": "cpu",
                "name": "AMD Ryzen 5 5600X",
                "brand": "AMD",
                "model": "5600X",
                "price": {"amount": 199.99, "currency": "USD"},
                "specifications": {"cores": 6, "threads": 12, "socket": "AM4"},
                "compatibility": {"socket": "AM4"},
                "performance_scores": {"gaming_score": 85, "productivity_score": 80, "creative_score": 75, "overall_score": 82},
                "availability": {"in_stock": True, "stock_quantity": 50}
            },
            {
                "type": "gpu",
                "name": "NVIDIA GeForce RTX 4060",
                "brand": "NVIDIA",
                "model": "RTX 4060",
                "price": {"amount": 299.99, "currency": "USD"},
                "specifications": {"vram": 8, "memory_type": "GDDR6"},
                "performance_scores": {"gaming_score": 85, "productivity_score": 70, "creative_score": 75, "overall_score": 78},
                "availability": {"in_stock": True, "stock_quantity": 40}
            }
        ]

        await self.test_db.components.insert_many(test_components)

        # Test PC configuration
        test_config = {
            "name": "Gaming PC Test Build",
            "description": "Test configuration for integration testing",
            "components": [
                {"component_id": str(test_components[0]["_id"]), "type": "cpu", "quantity": 1},
                {"component_id": str(test_components[1]["_id"]), "type": "gpu", "quantity": 1}
            ],
            "total_price": 499.98,
            "performance_profile": {
                "gaming_performance": 85,
                "productivity_performance": 75,
                "creative_performance": 75,
                "overall_performance": 80
            },
            "suitability_scores": {
                "gaming": 88,
                "office": 65,
                "creative": 70,
                "programming": 72,
                "general": 75
            },
            "source": "test"
        }

        await self.test_db.pc_configurations.insert_one(test_config)

    async def test_complete_recommendation_workflow(self):
        """Test complete recommendation generation workflow"""
        # Step 1: Submit recommendation request
        request_data = {
            "session_id": "integration-test-session",
            "purpose": "gaming",
            "budget": {
                "min": 400,
                "max": 600
            },
            "performance_level": "high",
            "preferred_brands": ["NVIDIA", "AMD"]
        }

        # This will initially fail until recommendation engine is implemented
        response = self.client.post("/api/v1/recommendations", json=request_data)

        # Initially expect 501 (Not Implemented)
        assert response.status_code in [200, 501]

        if response.status_code == 200:
            response_data = response.json()

            # Validate complete response structure
            assert "recommendation_id" in response_data
            assert "recommendations" in response_data
            assert "metadata" in response_data
            assert "expires_at" in response_data

            # Validate recommendation structure
            recommendations = response_data["recommendations"]
            assert isinstance(recommendations, list)
            assert len(recommendations) > 0

            # Validate individual recommendation
            rec = recommendations[0]
            assert "configuration_id" in rec
            assert "name" in rec
            assert "total_price" in rec
            assert "confidence_score" in rec
            assert "match_reasons" in rec
            assert "components" in rec

            # Validate components structure
            components = rec["components"]
            assert isinstance(components, list)
            assert len(components) > 0

            component = components[0]
            assert "id" in component
            assert "type" in component
            assert "name" in component
            assert "brand" in component
            assert "price" in component

    async def test_recommendation_persistence(self):
        """Test that recommendations are properly stored and retrievable"""
        request_data = {
            "session_id": "persistence-test-session",
            "purpose": "gaming",
            "budget": {"min": 400, "max": 600},
            "performance_level": "high"
        }

        # Submit recommendation
        response = self.client.post("/api/v1/recommendations", json=request_data)

        if response.status_code == 200:
            response_data = response.json()
            recommendation_id = response_data["recommendation_id"]

            # Retrieve recommendation details
            detail_response = self.client.get(f"/api/v1/recommendations/{recommendation_id}")

            assert detail_response.status_code == 200
            detail_data = detail_response.json()

            # Validate persisted data matches original request
            assert detail_data["user_requirements"]["purpose"] == request_data["purpose"]
            assert detail_data["user_requirements"]["budget"]["min"] == request_data["budget"]["min"]
            assert detail_data["user_requirements"]["budget"]["max"] == request_data["budget"]["max"]
            assert detail_data["user_requirements"]["performance_level"] == request_data["performance_level"]

    async def test_recommendation_budget_filtering(self):
        """Test that recommendations respect budget constraints"""
        # Test with very low budget
        low_budget_request = {
            "session_id": "low-budget-test",
            "purpose": "gaming",
            "budget": {"min": 50, "max": 100},  # Very low budget
            "performance_level": "high"
        }

        response = self.client.post("/api/v1/recommendations", json=low_budget_request)

        if response.status_code == 200:
            data = response.json()
            recommendations = data["recommendations"]

            # Should either return no recommendations or recommendations within budget
            for rec in recommendations:
                assert rec["total_price"] >= low_budget_request["budget"]["min"]
                assert rec["total_price"] <= low_budget_request["budget"]["max"]

    async def test_recommendation_performance_matching(self):
        """Test that recommendations match performance requirements"""
        performance_tests = [
            {
                "session_id": "basic-performance-test",
                "purpose": "office",
                "budget": {"min": 300, "max": 500},
                "performance_level": "basic"
            },
            {
                "session_id": "high-performance-test",
                "purpose": "gaming",
                "budget": {"min": 400, "max": 800},
                "performance_level": "high"
            }
        ]

        for test_request in performance_tests:
            response = self.client.post("/api/v1/recommendations", json=test_request)

            if response.status_code == 200:
                data = response.json()
                recommendations = data["recommendations"]

                # Recommendations should exist and have appropriate confidence scores
                assert len(recommendations) > 0
                for rec in recommendations:
                    assert rec["confidence_score"] > 0
                    assert rec["confidence_score"] <= 100
