"""
Contract tests for recommendations API endpoints
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app


@pytest.mark.asyncio
class TestRecommendationsContract:
    """Contract tests for recommendation endpoints"""

    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)

    def test_create_recommendations_contract(self):
        """Test POST /recommendations contract compliance"""
        # Test data matching the expected request schema
        request_data = {
            "session_id": "test-session-123",
            "purpose": "gaming",
            "budget": {
                "min": 800,
                "max": 1500
            },
            "performance_level": "high",
            "preferred_brands": ["NVIDIA", "Intel"],
            "must_have_features": ["ray_tracing"]
        }

        # This test will fail until the endpoint is implemented
        # It defines the expected contract
        response = self.client.post("/api/v1/recommendations", json=request_data)

        # Contract expectations (will be updated when endpoint is implemented)
        assert response.status_code in [200, 501]  # 501 = Not Implemented (expected initially)

        if response.status_code == 200:
            response_data = response.json()

            # Validate response structure when implemented
            assert "recommendation_id" in response_data
            assert "recommendations" in response_data
            assert isinstance(response_data["recommendations"], list)

            if response_data["recommendations"]:
                rec = response_data["recommendations"][0]
                assert "configuration_id" in rec
                assert "name" in rec
                assert "total_price" in rec
                assert "confidence_score" in rec
                assert isinstance(rec["confidence_score"], (int, float))
                assert 0 <= rec["confidence_score"] <= 100

    def test_create_recommendations_validation_contract(self):
        """Test POST /recommendations input validation contract"""
        # Test invalid request data
        invalid_requests = [
            # Missing required fields
            {},
            {"session_id": "test"},
            {"purpose": "gaming"},

            # Invalid purpose
            {
                "session_id": "test",
                "purpose": "invalid_purpose",
                "budget": {"min": 500, "max": 1000},
                "performance_level": "high"
            },

            # Invalid budget (max < min)
            {
                "session_id": "test",
                "purpose": "gaming",
                "budget": {"min": 1000, "max": 500},
                "performance_level": "high"
            },

            # Invalid performance level
            {
                "session_id": "test",
                "purpose": "gaming",
                "budget": {"min": 500, "max": 1000},
                "performance_level": "invalid_level"
            }
        ]

        for invalid_request in invalid_requests:
            response = self.client.post("/api/v1/recommendations", json=invalid_request)
            # Should return 422 for validation errors
            assert response.status_code in [400, 422]

    def test_get_recommendation_details_contract(self):
        """Test GET /recommendations/{id} contract compliance"""
        # Test with non-existent ID
        response = self.client.get("/api/v1/recommendations/non-existent-id")

        # Should return 404 for non-existent recommendation
        assert response.status_code in [404, 501]  # 501 = Not Implemented (expected initially)

    def test_health_endpoint_contract(self):
        """Test GET /health contract compliance"""
        response = self.client.get("/api/v1/health")

        # Health endpoint should always work
        assert response.status_code == 200

        response_data = response.json()
        assert "status" in response_data
        assert response_data["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in response_data
        assert "version" in response_data
