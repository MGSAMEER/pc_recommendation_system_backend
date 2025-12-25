"""
Integration tests for recommendation engine dynamics
Tests that different inputs produce different outputs
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.api.models.user_profile import UserProfile, Budget
from app.api.services.recommendation_engine import RecommendationEngine


@pytest.mark.asyncio
async def test_different_purposes_produce_different_results():
    """Test that different purposes produce different recommendations"""
    engine = RecommendationEngine()
    
    # Mock database
    mock_configs = [
        {
            '_id': '1',
            'name': 'Gaming PC',
            'total_price': 1500,
            'suitability_scores': {'gaming': 90, 'office': 60, 'creative': 70},
            'performance_profile': {'overall_performance': 85, 'cpu_performance': 80, 'gpu_performance': 90},
            'components': []
        },
        {
            '_id': '2',
            'name': 'Office PC',
            'total_price': 1200,
            'suitability_scores': {'gaming': 50, 'office': 90, 'creative': 60},
            'performance_profile': {'overall_performance': 70, 'cpu_performance': 75, 'gpu_performance': 60},
            'components': []
        }
    ]
    
    # Mock the database methods
    engine.configs_collection = AsyncMock()
    engine.configs_collection.aggregate = AsyncMock(return_value={
        'to_list': AsyncMock(return_value=mock_configs)
    })
    engine.components_collection = AsyncMock()
    
    # Test gaming purpose
    gaming_profile = UserProfile(
        session_id='test1',
        purpose='gaming',
        budget=Budget(min=1000, max=2000),
        performance_level='high',
        preferred_brands=['NVIDIA']
    )
    
    # Test office purpose
    office_profile = UserProfile(
        session_id='test2',
        purpose='office',
        budget=Budget(min=1000, max=2000),
        performance_level='basic',
        preferred_brands=['Intel']
    )
    
    # Initialize engine
    await engine.initialize()
    
    # Get recommendations
    gaming_recs = await engine.generate_recommendations(gaming_profile, 2)
    office_recs = await engine.generate_recommendations(office_profile, 2)
    
    # Verify different results
    assert len(gaming_recs) > 0
    assert len(office_recs) > 0
    
    # Top recommendations should be different
    assert gaming_recs[0]['name'] != office_recs[0]['name']
    assert gaming_recs[0]['confidence_score'] != office_recs[0]['confidence_score']
    
    # Gaming should have higher score for gaming PC
    gaming_pc_score = next(rec['confidence_score'] for rec in gaming_recs if rec['name'] == 'Gaming PC')
    office_pc_score = next(rec['confidence_score'] for rec in office_recs if rec['name'] == 'Gaming PC')
    
    assert gaming_pc_score > office_pc_score


@pytest.mark.asyncio
async def test_different_budgets_produce_different_results():
    """Test that different budget ranges produce different recommendations"""
    engine = RecommendationEngine()
    
    # Mock database
    mock_configs = [
        {
            '_id': '1',
            'name': 'Budget PC',
            'total_price': 800,
            'suitability_scores': {'gaming': 60, 'office': 80},
            'performance_profile': {'overall_performance': 65},
            'components': []
        },
        {
            '_id': '2',
            'name': 'Mid-Range PC',
            'total_price': 1500,
            'suitability_scores': {'gaming': 80, 'office': 70},
            'performance_profile': {'overall_performance': 80},
            'components': []
        },
        {
            '_id': '3',
            'name': 'High-End PC',
            'total_price': 2500,
            'suitability_scores': {'gaming': 95, 'office': 60},
            'performance_profile': {'overall_performance': 90},
            'components': []
        }
    ]
    
    # Mock the database methods
    engine.configs_collection = AsyncMock()
    engine.configs_collection.aggregate = AsyncMock(return_value={
        'to_list': AsyncMock(return_value=mock_configs)
    })
    engine.components_collection = AsyncMock()
    
    # Test tight budget
    tight_budget_profile = UserProfile(
        session_id='test1',
        purpose='gaming',
        budget=Budget(min=700, max=900),
        performance_level='standard',
        preferred_brands=[]
    )
    
    # Test flexible budget
    flexible_budget_profile = UserProfile(
        session_id='test2',
        purpose='gaming',
        budget=Budget(min=1000, max=3000),
        performance_level='high',
        preferred_brands=[]
    )
    
    # Initialize engine
    await engine.initialize()
    
    # Get recommendations
    tight_recs = await engine.generate_recommendations(tight_budget_profile, 2)
    flexible_recs = await engine.generate_recommendations(flexible_budget_profile, 2)
    
    # Verify different results
    assert len(tight_recs) > 0
    assert len(flexible_recs) > 0
    
    # Tight budget should only include budget PC
    assert tight_recs[0]['name'] == 'Budget PC'
    assert tight_recs[0]['total_price'] == 800
    
    # Flexible budget should have higher-end options
    assert flexible_recs[0]['total_price'] > 1000
    assert flexible_recs[0]['name'] != 'Budget PC'


@pytest.mark.asyncio
async def test_different_performance_levels_produce_different_results():
    """Test that different performance levels produce different recommendations"""
    engine = RecommendationEngine()
    
    # Mock database
    mock_configs = [
        {
            '_id': '1',
            'name': 'Basic PC',
            'total_price': 1200,
            'suitability_scores': {'gaming': 50},
            'performance_profile': {'overall_performance': 40, 'cpu_performance': 45, 'gpu_performance': 35},
            'components': []
        },
        {
            '_id': '2',
            'name': 'High-End PC',
            'total_price': 2000,
            'suitability_scores': {'gaming': 90},
            'performance_profile': {'overall_performance': 85, 'cpu_performance': 80, 'gpu_performance': 90},
            'components': []
        }
    ]
    
    # Mock the database methods
    engine.configs_collection = AsyncMock()
    engine.configs_collection.aggregate = AsyncMock(return_value={
        'to_list': AsyncMock(return_value=mock_configs)
    })
    engine.components_collection = AsyncMock()
    
    # Test basic performance
    basic_profile = UserProfile(
        session_id='test1',
        purpose='gaming',
        budget=Budget(min=1000, max=2500),
        performance_level='basic',
        preferred_brands=[]
    )
    
    # Test professional performance
    pro_profile = UserProfile(
        session_id='test2',
        purpose='gaming',
        budget=Budget(min=1000, max=2500),
        performance_level='professional',
        preferred_brands=[]
    )
    
    # Initialize engine
    await engine.initialize()
    
    # Get recommendations
    basic_recs = await engine.generate_recommendations(basic_profile, 2)
    pro_recs = await engine.generate_recommendations(pro_profile, 2)
    
    # Verify different results
    assert len(basic_recs) > 0
    assert len(pro_recs) > 0
    
    # Professional should have higher score for high-end PC
    basic_high_end_score = next(rec['confidence_score'] for rec in basic_recs if rec['name'] == 'High-End PC')
    pro_high_end_score = next(rec['confidence_score'] for rec in pro_recs if rec['name'] == 'High-End PC')
    
    assert pro_high_end_score > basic_high_end_score
    
    # Professional should rank high-end PC higher
    assert pro_recs[0]['name'] == 'High-End PC'


@pytest.mark.asyncio
async def test_different_brands_produce_different_results():
    """Test that brand preferences affect recommendations"""
    engine = RecommendationEngine()
    
    # Mock database with brand information
    mock_configs = [
        {
            '_id': '1',
            'name': 'NVIDIA PC',
            'total_price': 1500,
            'suitability_scores': {'gaming': 85},
            'performance_profile': {'overall_performance': 80},
            'components': [
                {'component_id': 'gpu1', 'type': 'gpu'},
                {'component_id': 'cpu1', 'type': 'cpu'}
            ]
        },
        {
            '_id': '2',
            'name': 'AMD PC',
            'total_price': 1400,
            'suitability_scores': {'gaming': 80},
            'performance_profile': {'overall_performance': 75},
            'components': [
                {'component_id': 'gpu2', 'type': 'gpu'},
                {'component_id': 'cpu2', 'type': 'cpu'}
            ]
        }
    ]
    
    # Mock components
    mock_components = [
        {'_id': 'gpu1', 'brand': 'NVIDIA', 'name': 'RTX 4080', 'type': 'gpu'},
        {'_id': 'cpu1', 'brand': 'Intel', 'name': 'i7-13700K', 'type': 'cpu'},
        {'_id': 'gpu2', 'brand': 'AMD', 'name': 'RX 7800 XT', 'type': 'gpu'},
        {'_id': 'cpu2', 'brand': 'AMD', 'name': 'Ryzen 7 7800X3D', 'type': 'cpu'}
    ]
    
    # Mock the database methods
    engine.configs_collection = AsyncMock()
    engine.configs_collection.aggregate = AsyncMock(return_value={
        'to_list': AsyncMock(return_value=mock_configs)
    })
    engine.components_collection = AsyncMock()
    engine.components_collection.find = AsyncMock(return_value={
        'to_list': AsyncMock(return_value=mock_components)
    })
    
    # Test with NVIDIA preference
    nvidia_profile = UserProfile(
        session_id='test1',
        purpose='gaming',
        budget=Budget(min=1000, max=2000),
        performance_level='high',
        preferred_brands=['NVIDIA']
    )
    
    # Test with AMD preference
    amd_profile = UserProfile(
        session_id='test2',
        purpose='gaming',
        budget=Budget(min=1000, max=2000),
        performance_level='high',
        preferred_brands=['AMD']
    )
    
    # Test with no preference
    no_pref_profile = UserProfile(
        session_id='test3',
        purpose='gaming',
        budget=Budget(min=1000, max=2000),
        performance_level='high',
        preferred_brands=[]
    )
    
    # Initialize engine
    await engine.initialize()
    
    # Get recommendations
    nvidia_recs = await engine.generate_recommendations(nvidia_profile, 2)
    amd_recs = await engine.generate_recommendations(amd_profile, 2)
    no_pref_recs = await engine.generate_recommendations(no_pref_profile, 2)
    
    # Verify different results
    assert len(nvidia_recs) > 0
    assert len(amd_recs) > 0
    assert len(no_pref_recs) > 0
    
    # NVIDIA preference should boost NVIDIA PC score
    nvidia_pc_nvidia_score = next(rec['confidence_score'] for rec in nvidia_recs if rec['name'] == 'NVIDIA PC')
    nvidia_pc_amd_score = next(rec['confidence_score'] for rec in amd_recs if rec['name'] == 'NVIDIA PC')
    nvidia_pc_no_pref_score = next(rec['confidence_score'] for rec in no_pref_recs if rec['name'] == 'NVIDIA PC')
    
    assert nvidia_pc_nvidia_score > nvidia_pc_amd_score
    assert nvidia_pc_nvidia_score > nvidia_pc_no_pref_score
    
    # AMD preference should boost AMD PC score
    amd_pc_nvidia_score = next(rec['confidence_score'] for rec in nvidia_recs if rec['name'] == 'AMD PC')
    amd_pc_amd_score = next(rec['confidence_score'] for rec in amd_recs if rec['name'] == 'AMD PC')
    amd_pc_no_pref_score = next(rec['confidence_score'] for rec in no_pref_recs if rec['name'] == 'AMD PC')
    
    assert amd_pc_amd_score > amd_pc_nvidia_score
    assert amd_pc_amd_score > amd_pc_no_pref_score


@pytest.mark.asyncio
async def test_cache_invalidation_on_different_inputs():
    """Test that cache properly invalidates when inputs change"""
    engine = RecommendationEngine()
    
    # Mock database
    mock_configs = [
        {
            '_id': '1',
            'name': 'Test PC',
            'total_price': 1500,
            'suitability_scores': {'gaming': 80},
            'performance_profile': {'overall_performance': 75},
            'components': []
        }
    ]
    
    # Mock the database methods
    engine.configs_collection = AsyncMock()
    engine.configs_collection.aggregate = AsyncMock(return_value={
        'to_list': AsyncMock(return_value=mock_configs)
    })
    engine.components_collection = AsyncMock()
    
    # Test profile 1
    profile1 = UserProfile(
        session_id='test1',
        purpose='gaming',
        budget=Budget(min=1000, max=2000),
        performance_level='high',
        preferred_brands=['NVIDIA']
    )
    
    # Test profile 2 (different purpose)
    profile2 = UserProfile(
        session_id='test1',  # Same session ID
        purpose='office',    # Different purpose
        budget=Budget(min=1000, max=2000),
        performance_level='high',
        preferred_brands=['NVIDIA']
    )
    
    # Initialize engine
    await engine.initialize()
    
    # Clear cache first
    from app.core.cache import cache
    await cache.clear()
    
    # Get recommendations for profile 1
    recs1_first = await engine.generate_recommendations(profile1, 1)
    
    # Get recommendations for profile 2 (should not use cache)
    recs2 = await engine.generate_recommendations(profile2, 1)
    
    # Get recommendations for profile 1 again (should use cache)
    recs1_second = await engine.generate_recommendations(profile1, 1)
    
    # Verify different results for different profiles
    assert recs1_first[0]['confidence_score'] != recs2[0]['confidence_score']
    
    # Verify cache works for same profile
    assert recs1_first[0]['confidence_score'] == recs1_second[0]['confidence_score']


@pytest.mark.asyncio
async def test_extreme_input_filtering():
    """Test that extreme inputs properly filter results"""
    engine = RecommendationEngine()
    
    # Mock database with various price points
    mock_configs = [
        {
            '_id': '1',
            'name': 'Budget PC',
            'total_price': 500,  # Very cheap
            'suitability_scores': {'gaming': 40},
            'performance_profile': {'overall_performance': 30},
            'components': []
        },
        {
            '_id': '2',
            'name': 'Mid-Range PC',
            'total_price': 1500,
            'suitability_scores': {'gaming': 70},
            'performance_profile': {'overall_performance': 65},
            'components': []
        },
        {
            '_id': '3',
            'name': 'High-End PC',
            'total_price': 3000,  # Expensive
            'suitability_scores': {'gaming': 90},
            'performance_profile': {'overall_performance': 85},
            'components': []
        }
    ]
    
    # Mock the database methods
    engine.configs_collection = AsyncMock()
    engine.configs_collection.aggregate = AsyncMock(return_value={
        'to_list': AsyncMock(return_value=mock_configs)
    })
    engine.components_collection = AsyncMock()
    
    # Test extremely low budget (should only return budget PC)
    low_budget_profile = UserProfile(
        session_id='test1',
        purpose='gaming',
        budget=Budget(min=100, max=600),  # Very tight budget
        performance_level='basic',
        preferred_brands=[]
    )
    
    # Test extremely high budget (should exclude budget PC)
    high_budget_profile = UserProfile(
        session_id='test2',
        purpose='gaming',
        budget=Budget(min=2000, max=5000),  # High budget
        performance_level='professional',
        preferred_brands=[]
    )
    
    # Test unrealistic budget (should return no results)
    unrealistic_profile = UserProfile(
        session_id='test3',
        purpose='gaming',
        budget=Budget(min=10000, max=20000),  # Unrealistic budget
        performance_level='professional',
        preferred_brands=[]
    )
    
    # Initialize engine
    await engine.initialize()
    
    # Get recommendations
    low_budget_recs = await engine.generate_recommendations(low_budget_profile, 3)
    high_budget_recs = await engine.generate_recommendations(high_budget_profile, 3)
    unrealistic_recs = await engine.generate_recommendations(unrealistic_profile, 3)
    
    # Verify low budget filtering
    assert len(low_budget_recs) == 1  # Should only get budget PC
    assert low_budget_recs[0]['name'] == 'Budget PC'
    assert low_budget_recs[0]['total_price'] == 500
    
    # Verify high budget filtering
    assert len(high_budget_recs) == 1  # Should only get high-end PC
    assert high_budget_recs[0]['name'] == 'High-End PC'
    assert high_budget_recs[0]['total_price'] == 3000
    
    # Verify unrealistic budget returns empty
    assert len(unrealistic_recs) == 0  # No PCs in this price range


@pytest.mark.asyncio
async def test_extreme_performance_requirements():
    """Test that extreme performance requirements affect scoring"""
    engine = RecommendationEngine()

    # Mock database
    mock_configs = [
        {
            '_id': '1',
            'name': 'Basic PC',
            'total_price': 1200,
            'suitability_scores': {'gaming': 50},
            'performance_profile': {'overall_performance': 40, 'cpu_performance': 45, 'gpu_performance': 35},
            'components': []
        },
        {
            '_id': '2',
            'name': 'High-End PC',
            'total_price': 2000,
            'suitability_scores': {'gaming': 90},
            'performance_profile': {'overall_performance': 85, 'cpu_performance': 80, 'gpu_performance': 90},
            'components': []
        }
    ]

    # Mock the database methods
    engine.configs_collection = AsyncMock()
    engine.configs_collection.aggregate = AsyncMock(return_value={
        'to_list': AsyncMock(return_value=mock_configs)
    })
    engine.components_collection = AsyncMock()

    # Test basic performance requirement
    basic_profile = UserProfile(
        session_id='test1',
        purpose='gaming',
        budget=Budget(min=1000, max=2500),
        performance_level='basic',
        preferred_brands=[]
    )

    # Test professional performance requirement
    pro_profile = UserProfile(
        session_id='test2',
        purpose='gaming',
        budget=Budget(min=1000, max=2500),
        performance_level='professional',
        preferred_brands=[]
    )

    # Initialize engine
    await engine.initialize()

    # Get recommendations
    basic_recs = await engine.generate_recommendations(basic_profile, 2)
    pro_recs = await engine.generate_recommendations(pro_profile, 2)

    # Verify different scoring for same configs with different requirements
    assert len(basic_recs) == 2
    assert len(pro_recs) == 2

    # Professional should give higher score to high-end PC
    basic_high_end_score = next(rec['confidence_score'] for rec in basic_recs if rec['name'] == 'High-End PC')
    pro_high_end_score = next(rec['confidence_score'] for rec in pro_recs if rec['name'] == 'High-End PC')

    assert pro_high_end_score > basic_high_end_score

    # Professional should rank high-end PC first
    assert pro_recs[0]['name'] == 'High-End PC'
    assert pro_recs[0]['confidence_score'] > pro_recs[1]['confidence_score']


@pytest.mark.asyncio
async def test_database_query_structure():
    """Test that the database query properly filters by purpose and performance"""
    engine = RecommendationEngine()

    # Test with different purposes to ensure different results
    gaming_profile = UserProfile(
        session_id='gaming_test',
        purpose='gaming',
        budget=Budget(min=1000, max=2000),
        performance_level='high',
        preferred_brands=[]
    )

    office_profile = UserProfile(
        session_id='office_test',
        purpose='office',
        budget=Budget(min=1000, max=2000),
        performance_level='basic',
        preferred_brands=[]
    )

    # Initialize engine
    await engine.initialize()

    # Get recommendations - these should use real database queries
    gaming_recs = await engine.generate_recommendations(gaming_profile, 3)
    office_recs = await engine.generate_recommendations(office_profile, 3)

    # Verify we got results
    assert len(gaming_recs) > 0
    assert len(office_recs) > 0

    # Check that the recommendations are different
    gaming_names = set(rec['name'] for rec in gaming_recs)
    office_names = set(rec['name'] for rec in office_recs)

    # At minimum, the top recommendations should be different
    assert gaming_recs[0]['name'] != office_recs[0]['name']

    # Scores should also be different due to different purpose weighting
    gaming_top_score = gaming_recs[0]['confidence_score']
    office_top_score = office_recs[0]['confidence_score']

    # The scores should be meaningfully different (not just rounding differences)
    assert abs(gaming_top_score - office_top_score) > 5


@pytest.mark.asyncio
async def test_dynamic_weighting_system():
    """Test that dynamic weighting produces different scores for same config with different inputs"""
    engine = RecommendationEngine()
    
    # Mock database
    mock_config = [
        {
            '_id': '1',
            'name': 'Test PC',
            'total_price': 1500,
            'suitability_scores': {'gaming': 80, 'office': 60},
            'performance_profile': {'overall_performance': 75, 'cpu_performance': 70, 'gpu_performance': 80},
            'components': []
        }
    ]
    
    # Mock the database methods
    engine.configs_collection = AsyncMock()
    engine.configs_collection.aggregate = AsyncMock(return_value={
        'to_list': AsyncMock(return_value=mock_config)
    })
    engine.components_collection = AsyncMock()
    
    # Test tight budget (should emphasize budget fit)
    tight_budget_profile = UserProfile(
        session_id='test1',
        purpose='gaming',
        budget=Budget(min=1400, max=1600),  # Very tight range
        performance_level='high',
        preferred_brands=[]
    )
    
    # Test flexible budget (should emphasize performance)
    flexible_budget_profile = UserProfile(
        session_id='test2',
        purpose='gaming',
        budget=Budget(min=1000, max=3000),  # Flexible range
        performance_level='high',
        preferred_brands=[]
    )
    
    # Initialize engine
    await engine.initialize()
    
    # Get recommendations
    tight_recs = await engine.generate_recommendations(tight_budget_profile, 1)
    flexible_recs = await engine.generate_recommendations(flexible_budget_profile, 1)
    
    # Verify different scores due to dynamic weighting
    assert len(tight_recs) > 0
    assert len(flexible_recs) > 0
    
    # Scores should be different due to different weightings
    assert tight_recs[0]['confidence_score'] != flexible_recs[0]['confidence_score']
    
    # Check that weights are different in match reasons
    tight_weights = {reason['factor']: reason['weight'] for reason in tight_recs[0]['match_reasons']}
    flexible_weights = {reason['factor']: reason['weight'] for reason in flexible_recs[0]['match_reasons']}
    
    # Budget should have higher weight in tight budget scenario
    assert tight_weights['budget_fit'] > flexible_weights['budget_fit']
    
    # Performance should have higher weight in flexible budget scenario
    assert flexible_weights['performance_match'] > tight_weights['performance_match']
