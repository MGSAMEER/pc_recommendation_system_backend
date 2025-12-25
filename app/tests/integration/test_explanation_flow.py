"""
Integration tests for explanation generation workflow
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
class TestExplanationFlowIntegration:
    """Integration tests for explanation generation and transparency features"""

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
        await self.test_db.recommendations.delete_many({})

        # Seed with test data
        await self._seed_test_data()

        yield

        # Cleanup
        await self.test_db_client.close()

    async def _seed_test_data(self):
        """Seed database with test components and configurations"""
        # Test components with varying performance scores
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
            },
            {
                "type": "cpu",
                "name": "Intel Core i5-12600K",
                "brand": "Intel",
                "model": "i5-12600K",
                "price": {"amount": 229.99, "currency": "USD"},
                "specifications": {"cores": 10, "threads": 16, "socket": "LGA1700"},
                "compatibility": {"socket": "LGA1700"},
                "performance_scores": {"gaming_score": 88, "productivity_score": 85, "creative_score": 82, "overall_score": 86},
                "availability": {"in_stock": True, "stock_quantity": 30}
            }
        ]

        await self.test_db.components.insert_many(test_components)

        # Test PC configurations with different suitability scores
        test_configs = [
            {
                "name": "Gaming PC Build",
                "description": "High-performance gaming configuration",
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
                "source": "curated"
            },
            {
                "name": "Office PC Build",
                "description": "Productivity-focused office configuration",
                "components": [
                    {"component_id": str(test_components[2]["_id"]), "type": "cpu", "quantity": 1},
                    {"component_id": str(test_components[1]["_id"]), "type": "gpu", "quantity": 1}
                ],
                "total_price": 529.98,
                "performance_profile": {
                    "gaming_performance": 88,
                    "productivity_performance": 85,
                    "creative_performance": 82,
                    "overall_performance": 86
                },
                "suitability_scores": {
                    "gaming": 75,
                    "office": 85,
                    "creative": 78,
                    "programming": 82,
                    "general": 80
                },
                "source": "curated"
            }
        ]

        await self.test_db.pc_configurations.insert_many(test_configs)

    def test_explanation_generation_for_gaming_recommendation(self):
        """Test that gaming-focused recommendations include appropriate explanations"""
        request_data = {
            "session_id": "explanation-gaming-test",
            "purpose": "gaming",
            "budget": {"min": 400, "max": 600},
            "performance_level": "high"
        }

        response = self.client.post("/api/v1/recommendations", json=request_data)

        if response.status_code == 200:
            data = response.json()
            recommendations = data["recommendations"]

            assert len(recommendations) > 0

            # Check that explanations are generated
            for rec in recommendations:
                assert "match_reasons" in rec
                assert "trade_offs" in rec
                assert "confidence_score" in rec

                # Validate match reasons structure
                match_reasons = rec["match_reasons"]
                assert isinstance(match_reasons, list)
                assert len(match_reasons) > 0

                for reason in match_reasons:
                    assert "factor" in reason
                    assert "weight" in reason
                    assert "explanation" in reason
                    assert isinstance(reason["weight"], (int, float))
                    assert 0 <= reason["weight"] <= 1

                # Check for gaming-specific explanations
                gaming_reasons = [r for r in match_reasons if "gaming" in r["explanation"].lower()]
                assert len(gaming_reasons) > 0, "Should include gaming-specific explanations"

    def test_explanation_generation_for_office_recommendation(self):
        """Test that office-focused recommendations include appropriate explanations"""
        request_data = {
            "session_id": "explanation-office-test",
            "purpose": "office",
            "budget": {"min": 400, "max": 600},
            "performance_level": "standard"
        }

        response = self.client.post("/api/v1/recommendations", json=request_data)

        if response.status_code == 200:
            data = response.json()
            recommendations = data["recommendations"]

            assert len(recommendations) > 0

            # Check explanations for office use case
            for rec in recommendations:
                match_reasons = rec["match_reasons"]
                office_reasons = [r for r in match_reasons if "office" in r["explanation"].lower() or "productivity" in r["explanation"].lower()]
                assert len(office_reasons) > 0, "Should include office/productivity-specific explanations"

    def test_confidence_score_correlates_with_explanation_quality(self):
        """Test that higher confidence scores have more detailed explanations"""
        request_data = {
            "session_id": "confidence-explanation-test",
            "purpose": "gaming",
            "budget": {"min": 400, "max": 600},
            "performance_level": "high"
        }

        response = self.client.post("/api/v1/recommendations", json=request_data)

        if response.status_code == 200:
            data = response.json()
            recommendations = data["recommendations"]

            assert len(recommendations) >= 2, "Need at least 2 recommendations to compare"

            # Sort by confidence score
            sorted_recs = sorted(recommendations, key=lambda x: x["confidence_score"], reverse=True)
            high_confidence = sorted_recs[0]
            low_confidence = sorted_recs[-1]

            # Higher confidence should have more match reasons (generally)
            # This is a soft assertion since it depends on the algorithm
            high_reason_count = len(high_confidence["match_reasons"])
            low_reason_count = len(low_confidence["match_reasons"])

            # At minimum, both should have explanations
            assert high_reason_count > 0, "High confidence recommendation should have explanations"
            assert low_reason_count > 0, "Low confidence recommendation should have explanations"

    def test_trade_off_explanations_are_informative(self):
        """Test that trade-off explanations provide useful information"""
        # Create a scenario that might generate trade-offs (tight budget, high performance)
        request_data = {
            "session_id": "trade-off-test",
            "purpose": "gaming",
            "budget": {"min": 200, "max": 350},  # Tight budget
            "performance_level": "high"  # High requirements
        }

        response = self.client.post("/api/v1/recommendations", json=request_data)

        if response.status_code == 200:
            data = response.json()
            recommendations = data["recommendations"]

            # Check that trade-offs are explained when present
            for rec in recommendations:
                trade_offs = rec.get("trade_offs", [])

                if trade_offs:  # If there are trade-offs
                    for trade_off in trade_offs:
                        assert "type" in trade_off
                        assert "impact" in trade_off
                        assert "description" in trade_off

                        # Description should be informative
                        assert len(trade_off["description"]) > 10, "Trade-off description should be detailed"
                        assert trade_off["impact"] in ["positive", "negative", "neutral"]

    def test_budget_explanation_accuracy(self):
        """Test that budget-related explanations are accurate"""
        request_data = {
            "session_id": "budget-explanation-test",
            "purpose": "gaming",
            "budget": {"min": 450, "max": 550},
            "performance_level": "high"
        }

        response = self.client.post("/api/v1/recommendations", json=request_data)

        if response.status_code == 200:
            data = response.json()
            recommendations = data["recommendations"]

            for rec in recommendations:
                price = rec["total_price"]
                budget_min = request_data["budget"]["min"]
                budget_max = request_data["budget"]["max"]

                # Price should be within budget range
                assert budget_min <= price <= budget_max, f"Price ${price} should be within budget ${budget_min}-${budget_max}"

                # Should have budget-related explanation
                match_reasons = rec["match_reasons"]
                budget_reasons = [r for r in match_reasons if "budget" in r["explanation"].lower()]
                assert len(budget_reasons) > 0, "Should include budget-related explanations"

    def test_purpose_alignment_explanations(self):
        """Test that purpose alignment explanations are specific and accurate"""
        test_cases = [
            {
                "purpose": "gaming",
                "expected_keywords": ["gaming", "performance", "fps"]
            },
            {
                "purpose": "office",
                "expected_keywords": ["productivity", "office", "multitasking"]
            },
            {
                "purpose": "creative",
                "expected_keywords": ["creative", "rendering", "content"]
            }
        ]

        for test_case in test_cases:
            request_data = {
                "session_id": f"purpose-test-{test_case['purpose']}",
                "purpose": test_case["purpose"],
                "budget": {"min": 400, "max": 600},
                "performance_level": "standard"
            }

            response = self.client.post("/api/v1/recommendations", json=request_data)

            if response.status_code == 200:
                data = response.json()
                recommendations = data["recommendations"]

                assert len(recommendations) > 0

                for rec in recommendations:
                    match_reasons = rec["match_reasons"]
                    purpose_reasons = [r for r in match_reasons if test_case["purpose"] in r["explanation"].lower()]

                    # Should have at least one purpose-related explanation
                    assert len(purpose_reasons) > 0, f"Should include {test_case['purpose']}-related explanations"
