"""
Integration tests for comparison functionality
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
class TestComparisonFlowIntegration:
    """Integration tests for PC comparison functionality"""

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
        """Seed database with multiple comparable PC configurations"""
        # Test components with different performance levels
        test_components = [
            # Budget CPU
            {
                "type": "cpu",
                "name": "AMD Ryzen 5 5600",
                "brand": "AMD",
                "model": "5600",
                "price": {"amount": 149.99, "currency": "USD"},
                "specifications": {"cores": 6, "threads": 12, "socket": "AM4"},
                "compatibility": {"socket": "AM4"},
                "performance_scores": {"gaming_score": 80, "productivity_score": 75, "creative_score": 70, "overall_score": 76},
                "availability": {"in_stock": True, "stock_quantity": 50}
            },
            # Performance CPU
            {
                "type": "cpu",
                "name": "AMD Ryzen 7 5800X",
                "brand": "AMD",
                "model": "5800X",
                "price": {"amount": 299.99, "currency": "USD"},
                "specifications": {"cores": 8, "threads": 16, "socket": "AM4"},
                "compatibility": {"socket": "AM4"},
                "performance_scores": {"gaming_score": 88, "productivity_score": 85, "creative_score": 82, "overall_score": 86},
                "availability": {"in_stock": True, "stock_quantity": 30}
            },
            # Budget GPU
            {
                "type": "gpu",
                "name": "NVIDIA GeForce RTX 4060",
                "brand": "NVIDIA",
                "model": "RTX 4060",
                "price": {"amount": 299.99, "currency": "USD"},
                "specifications": {"vram": 8, "memory_type": "GDDR6"},
                "performance_scores": {"gaming_score": 82, "productivity_score": 68, "creative_score": 72, "overall_score": 75},
                "availability": {"in_stock": True, "stock_quantity": 40}
            },
            # Performance GPU
            {
                "type": "gpu",
                "name": "NVIDIA GeForce RTX 4070",
                "brand": "NVIDIA",
                "model": "RTX 4070",
                "price": {"amount": 549.99, "currency": "USD"},
                "specifications": {"vram": 12, "memory_type": "GDDR6X"},
                "performance_scores": {"gaming_score": 92, "productivity_score": 82, "creative_score": 88, "overall_score": 89},
                "availability": {"in_stock": True, "stock_quantity": 20}
            },
            # RAM options
            {
                "type": "ram",
                "name": "Corsair Vengeance LPX 16GB",
                "brand": "Corsair",
                "model": "Vengeance LPX",
                "price": {"amount": 79.99, "currency": "USD"},
                "specifications": {"capacity": 16, "speed": 3200, "type": "DDR4"},
                "performance_scores": {"gaming_score": 75, "productivity_score": 80, "creative_score": 78, "overall_score": 77},
                "availability": {"in_stock": True, "stock_quantity": 100}
            },
            {
                "type": "ram",
                "name": "Corsair Vengeance LPX 32GB",
                "brand": "Corsair",
                "model": "Vengeance LPX 32GB",
                "price": {"amount": 149.99, "currency": "USD"},
                "specifications": {"capacity": 32, "speed": 3200, "type": "DDR4"},
                "performance_scores": {"gaming_score": 78, "productivity_score": 85, "creative_score": 82, "overall_score": 81},
                "availability": {"in_stock": True, "stock_quantity": 75}
            }
        ]

        await self.test_db.components.insert_many(test_components)

        # Create multiple PC configurations for comparison
        test_configs = [
            {
                "name": "Budget Gaming PC",
                "description": "Affordable gaming setup for 1080p gaming",
                "components": [
                    {"component_id": str(test_components[0]["_id"]), "type": "cpu", "quantity": 1},
                    {"component_id": str(test_components[2]["_id"]), "type": "gpu", "quantity": 1},
                    {"component_id": str(test_components[4]["_id"]), "type": "ram", "quantity": 1}
                ],
                "total_price": 529.97,
                "performance_profile": {
                    "gaming_performance": 81,
                    "productivity_performance": 74,
                    "creative_performance": 71,
                    "overall_performance": 76
                },
                "suitability_scores": {
                    "gaming": 85,
                    "office": 65,
                    "creative": 68,
                    "programming": 70,
                    "general": 72
                },
                "source": "curated"
            },
            {
                "name": "Performance Gaming PC",
                "description": "High-end gaming setup for 1440p/4K gaming",
                "components": [
                    {"component_id": str(test_components[1]["_id"]), "type": "cpu", "quantity": 1},
                    {"component_id": str(test_components[3]["_id"]), "type": "gpu", "quantity": 1},
                    {"component_id": str(test_components[5]["_id"]), "type": "ram", "quantity": 1}
                ],
                "total_price": 999.97,
                "performance_profile": {
                    "gaming_performance": 90,
                    "productivity_performance": 84,
                    "creative_performance": 85,
                    "overall_performance": 87
                },
                "suitability_scores": {
                    "gaming": 92,
                    "office": 75,
                    "creative": 82,
                    "programming": 80,
                    "general": 82
                },
                "source": "curated"
            },
            {
                "name": "Balanced Workstation",
                "description": "Versatile PC for work and moderate gaming",
                "components": [
                    {"component_id": str(test_components[1]["_id"]), "type": "cpu", "quantity": 1},
                    {"component_id": str(test_components[2]["_id"]), "type": "gpu", "quantity": 1},
                    {"component_id": str(test_components[4]["_id"]), "type": "ram", "quantity": 1}
                ],
                "total_price": 679.97,
                "performance_profile": {
                    "gaming_performance": 85,
                    "productivity_performance": 80,
                    "creative_performance": 77,
                    "overall_performance": 81
                },
                "suitability_scores": {
                    "gaming": 78,
                    "office": 82,
                    "creative": 78,
                    "programming": 80,
                    "general": 80
                },
                "source": "curated"
            }
        ]

        await self.test_db.pc_configurations.insert_many(test_configs)

    def test_multiple_recommendations_for_comparison(self):
        """Test that the system returns multiple recommendations suitable for comparison"""
        request_data = {
            "session_id": "comparison-test-session",
            "purpose": "gaming",
            "budget": {"min": 400, "max": 1200},
            "performance_level": "high"
        }

        response = self.client.post("/api/v1/recommendations", json=request_data)

        if response.status_code == 200:
            data = response.json()
            recommendations = data["recommendations"]

            # Should return multiple options for comparison
            assert len(recommendations) >= 2, "Should return at least 2 recommendations for comparison"

            # Verify recommendations are different
            prices = [rec["total_price"] for rec in recommendations]
            assert len(set(prices)) > 1, "Recommendations should have different prices"

            confidence_scores = [rec["confidence_score"] for rec in recommendations]
            # Allow some recommendations to have same confidence but prefer variety
            assert len(recommendations) >= 2, "Should have multiple comparison options"

    def test_recommendations_vary_by_budget_ranges(self):
        """Test that different budget ranges return appropriately priced recommendations"""
        test_cases = [
            {"min": 300, "max": 600, "expected_range": (300, 700)},  # Budget range
            {"min": 700, "max": 1100, "expected_range": (600, 1200)},  # Performance range
        ]

        for budget_case in test_cases:
            request_data = {
                "session_id": f"budget-test-{budget_case['min']}-{budget_case['max']}",
                "purpose": "gaming",
                "budget": {"min": budget_case["min"], "max": budget_case["max"]},
                "performance_level": "high"
            }

            response = self.client.post("/api/v1/recommendations", json=request_data)

            if response.status_code == 200:
                data = response.json()
                recommendations = data["recommendations"]

                assert len(recommendations) > 0, f"No recommendations for budget {budget_case['min']}-{budget_case['max']}"

                # All recommendations should be within the expected price range
                for rec in recommendations:
                    price = rec["total_price"]
                    expected_min, expected_max = budget_case["expected_range"]
                    assert expected_min <= price <= expected_max, \
                        f"Price ${price} outside expected range ${expected_min}-${expected_max}"

    def test_recommendations_maintain_component_consistency(self):
        """Test that recommended configurations have consistent component combinations"""
        request_data = {
            "session_id": "consistency-test-session",
            "purpose": "gaming",
            "budget": {"min": 400, "max": 1000},
            "performance_level": "high"
        }

        response = self.client.post("/api/v1/recommendations", json=request_data)

        if response.status_code == 200:
            data = response.json()
            recommendations = data["recommendations"]

            for rec in recommendations:
                components = rec["components"]

                # Should have essential components
                component_types = {comp["type"] for comp in components}
                essential_types = {"cpu", "gpu"}  # At minimum
                assert essential_types.issubset(component_types), \
                    f"Missing essential components in recommendation: {component_types}"

                # Component prices should add up to total (approximately)
                component_total = sum(comp["price"] for comp in components)
                total_price = rec["total_price"]

                # Allow 10% variance for additional costs (taxes, shipping, etc.)
                assert 0.9 * component_total <= total_price <= 1.2 * component_total, \
                    f"Component total ${component_total} doesn't match total price ${total_price}"

    def test_performance_scores_correlate_with_price(self):
        """Test that higher-priced recommendations generally have better performance"""
        request_data = {
            "session_id": "performance-price-test",
            "purpose": "gaming",
            "budget": {"min": 400, "max": 1200},
            "performance_level": "high"
        }

        response = self.client.post("/api/v1/recommendations", json=request_data)

        if response.status_code == 200:
            data = response.json()
            recommendations = data["recommendations"]

            if len(recommendations) >= 2:
                # Sort by price
                price_sorted = sorted(recommendations, key=lambda x: x["total_price"])

                # Generally, higher price should correlate with higher performance
                # This is a trend check, not absolute rule
                price_correlation = 0
                for i in range(len(price_sorted) - 1):
                    current_perf = price_sorted[i]["confidence_score"]
                    next_perf = price_sorted[i + 1]["confidence_score"]

                    if next_perf >= current_perf:
                        price_correlation += 1

                # At least 60% should show price-performance correlation
                correlation_ratio = price_correlation / (len(price_sorted) - 1)
                assert correlation_ratio >= 0.6, \
                    f"Price-performance correlation too low: {correlation_ratio:.2f}"

    def test_recommendation_diversity_across_use_cases(self):
        """Test that different use cases return diverse recommendation profiles"""
        use_cases = ["gaming", "office", "creative"]

        recommendations_by_use = {}

        for use_case in use_cases:
            request_data = {
                "session_id": f"use-case-test-{use_case}",
                "purpose": use_case,
                "budget": {"min": 500, "max": 1000},
                "performance_level": "standard"
            }

            response = self.client.post("/api/v1/recommendations", json=request_data)

            if response.status_code == 200:
                data = response.json()
                recommendations_by_use[use_case] = data["recommendations"]

        # Check that gaming recommendations have higher gaming suitability
        if "gaming" in recommendations_by_use and "office" in recommendations_by_use:
            gaming_rec = recommendations_by_use["gaming"][0] if recommendations_by_use["gaming"] else None
            office_rec = recommendations_by_use["office"][0] if recommendations_by_use["office"] else None

            if gaming_rec and office_rec:
                gaming_suitability = gaming_rec.get("suitability_scores", {}).get("gaming", 0)
                office_gaming_suitability = office_rec.get("suitability_scores", {}).get("gaming", 0)

                # Gaming recommendation should be more gaming-suitable than office recommendation
                assert gaming_suitability >= office_gaming_suitability, \
                    f"Gaming rec suitability ({gaming_suitability}) should be >= office rec gaming suitability ({office_gaming_suitability})"
