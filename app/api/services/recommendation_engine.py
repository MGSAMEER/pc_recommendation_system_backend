"""
Recommendation engine for PC component matching
"""
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorCollection

from app.core.database import get_database
from app.core.cache import cache, generate_cache_key
from app.api.models.user_profile import UserProfile
from app.api.models.pc_config import PCConfiguration
from app.api.models.recommendation import Recommendation, MatchReason, TradeOff
import asyncio


logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Engine for generating PC recommendations based on user requirements"""

    def __init__(self):
        self.db = None
        self.components_collection = None
        self.configs_collection = None

    async def initialize(self):
        """Initialize database collections"""
        logger.info("Initializing recommendation engine...")
        self.db = await get_database()
        logger.info(f"Database object: {self.db}")
        self.components_collection = self.db.components
        self.configs_collection = self.db.pc_configurations
        logger.info(f"Collections initialized: components={self.components_collection}, configs={self.configs_collection}")

    async def generate_recommendations(
        self,
        user_profile: UserProfile,
        max_recommendations: int = 3,
        safe_mode: bool = False
    ) -> tuple[List[Dict[str, Any]], bool]:
        """
        Generate PC recommendations based on user profile with enhanced performance

        Args:
            user_profile: User requirements and preferences
            max_recommendations: Maximum number of recommendations to return

        Returns:
            List of recommendation dictionaries with confidence scores
        """
        logger.info(f"Starting recommendation generation for user: {user_profile.session_id} (safe_mode={safe_mode})")
        if safe_mode:
            logger.info("[SAFE MODE] Using stable, broad-compatibility recommendation logic")

        try:
            # Initialize collections if needed
            if self.configs_collection is None:
                await self.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize recommendation engine: {e}", exc_info=True)
            raise

        # Create cache key for user profile - include all relevant parameters to ensure different inputs produce different results
        # Note: session_id is NOT included so identical requirements produce identical results regardless of session
        # Use a hash of the normalized user profile for robustness
        normalized_profile = {
            "purpose": user_profile.purpose or "general",
            "budget_min": user_profile.budget.min if user_profile.budget else 0,
            "budget_max": user_profile.budget.max if user_profile.budget else 10000,
            "performance_level": user_profile.performance_level or "standard",
            "max_recommendations": max_recommendations,
            "safe_mode": safe_mode,
            "preferred_brands": sorted(user_profile.preferred_brands or []),
            "must_have_features": sorted(user_profile.must_have_features or [])
        }
        cache_key = generate_cache_key("recommendations", json.dumps(normalized_profile, sort_keys=True))

        # Try to get cached recommendations
        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.info(f"[CACHE HIT] Returning cached recommendations for user: {user_profile.session_id}")
            logger.debug(f"[CACHE] Key: {cache_key[:50]}..., User profile: purpose={user_profile.purpose}, budget=${user_profile.budget.min}-${user_profile.budget.max}, performance={user_profile.performance_level}")
            return cached_result, True

        logger.info(f"[CACHE MISS] Computing fresh recommendations for user: {user_profile.session_id}")
        logger.debug(f"[COMPUTE] Cache key: {cache_key[:50]}..., Profile: {user_profile.purpose}/{user_profile.performance_level}/${user_profile.budget.min}-{user_profile.budget.max}")


        # Get PC configurations with intelligent query based on user requirements
        try:
            logger.info(f"Processing request for purpose={user_profile.purpose}, budget=${user_profile.budget.min}-${user_profile.budget.max}, performance={user_profile.performance_level}")

            # Calculate suitability score threshold based on purpose and mode
            if safe_mode:
                # Safe mode: Use much broader thresholds for guaranteed results
                purpose_thresholds = {
                    'gaming': 30,      # Very broad for gaming
                    'creative': 25,    # Broad for creative work
                    'programming': 20, # Very broad for programming
                    'office': 15,      # Very broad for office
                    'general': 10      # Minimal threshold for general
                }
                min_suitability = purpose_thresholds.get(user_profile.purpose, 10)
                logger.info(f"[SAFE FILTERS] Broad suitability threshold: {user_profile.purpose} >= {min_suitability}")

                # Safe mode: Much lower performance requirements
                performance_thresholds = {
                    'basic': 15,
                    'standard': 20,
                    'high': 25,
                    'professional': 30
                }
                min_performance = performance_thresholds.get(user_profile.performance_level, 15)
                logger.info(f"[SAFE FILTERS] Broad performance threshold: {user_profile.performance_level} >= {min_performance}")
            else:
                # Normal mode: Use standard thresholds
                purpose_thresholds = {
                    'gaming': 60,      # Gaming PCs need good gaming scores
                    'creative': 55,    # Creative work needs decent scores
                    'programming': 50, # Programming is more flexible
                    'office': 45,      # Office work has lower requirements
                    'general': 40      # General purpose baseline
                }

                min_suitability = purpose_thresholds.get(user_profile.purpose, 40)
                logger.info(f"[FILTERS] Applied suitability threshold: {user_profile.purpose} >= {min_suitability}")

                # Calculate performance threshold based on required level
                performance_thresholds = {
                    'basic': 30,
                    'standard': 45,
                    'high': 60,
                    'professional': 75
                }

                min_performance = performance_thresholds.get(user_profile.performance_level, 40)
                logger.info(f"[FILTERS] Applied performance threshold: {user_profile.performance_level} >= {min_performance}")

            # Create dynamic field access for purpose suitability
            purpose_field = f"suitability_scores.{user_profile.purpose}"

            pipeline = [
                {
                    "$match": {
                        "suitability_scores": {"$exists": True},
                        "performance_profile": {"$exists": True},
                        "total_price": {
                            "$gte": user_profile.budget.min,
                            "$lte": user_profile.budget.max
                        },
                        # Filter by purpose suitability directly in match
                        purpose_field: {"$gte": min_suitability},
                        # Filter by performance level
                        "performance_profile.overall_performance": {"$gte": min_performance}
                    }
                },
                {
                    "$addFields": {
                        # Calculate a preliminary relevance score for sorting
                        "relevance_score": {
                            "$add": [
                                {"$multiply": [f"$suitability_scores.{user_profile.purpose}", 0.6]},
                                {"$multiply": ["$performance_profile.overall_performance", 0.4]}
                            ]
                        }
                    }
                },
                {
                    "$sort": {"relevance_score": -1, "total_price": 1}  # Sort by relevance, then price
                },
                {
                    "$limit": max_recommendations + 20  # Get more candidates for better selection
                }
            ]

            logger.info(f"[QUERY] Executing MongoDB aggregation pipeline with filters: budget=${user_profile.budget.min}-${user_profile.budget.max}, purpose={user_profile.purpose}, performance={user_profile.performance_level}")
            configs = await self.configs_collection.aggregate(pipeline).to_list(length=None)
            logger.info(f"[QUERY] Primary query returned {len(configs)} configurations")

            # Fallback: If we don't have enough configurations, broaden the search
            if len(configs) < max_recommendations:
                logger.warning(f"Intelligent query returned only {len(configs)} configs, need {max_recommendations}. Broadening search...")

                # Broaden the search by reducing thresholds
                fallback_min_suitability = max(20, min_suitability - 20)
                fallback_min_performance = max(20, min_performance - 20)

                fallback_pipeline = [
                    {
                        "$match": {
                            "suitability_scores": {"$exists": True},
                            "performance_profile": {"$exists": True},
                            "total_price": {
                                "$gte": user_profile.budget.min,
                                "$lte": user_profile.budget.max
                            },
                            # Use broader thresholds
                            purpose_field: {"$gte": fallback_min_suitability},
                            "performance_profile.overall_performance": {"$gte": fallback_min_performance}
                        }
                    },
                    {
                        "$addFields": {
                            "relevance_score": {
                                "$add": [
                                    {"$multiply": [f"$suitability_scores.{user_profile.purpose}", 0.6]},
                                    {"$multiply": ["$performance_profile.overall_performance", 0.4]}
                                ]
                            }
                        }
                    },
                    {
                        "$sort": {"relevance_score": -1, "total_price": 1}
                    },
                    {
                        "$limit": max_recommendations + 15
                    }
                ]

                fallback_configs = await self.configs_collection.aggregate(fallback_pipeline).to_list(length=None)
                logger.info(f"Fallback query found {len(fallback_configs)} configurations")

                # Combine results, preferring the more relevant ones
                combined_configs = configs + fallback_configs
                # Remove duplicates based on _id
                seen_ids = set()
                unique_configs = []
                for config in combined_configs:
                    config_id = str(config.get('_id'))
                    if config_id not in seen_ids:
                        seen_ids.add(config_id)
                        unique_configs.append(config)

                configs = unique_configs[:max_recommendations + 20]  # Limit to reasonable number
                logger.info(f"After combining and deduplicating: {len(configs)} unique configurations")


        except Exception as e:
            logger.warning(f"Aggregation failed, falling back to simple query: {e}")
            # Fallback to simple query
            configs_cursor = self.configs_collection.find({
                "total_price": {
                    "$gte": user_profile.budget.min,
                    "$lte": user_profile.budget.max
                }
            })
            configs = await configs_cursor.to_list(length=max_recommendations + 10)

        # Implement progressive fallback strategy if no configurations found
        if not configs:
            logger.warning("No PC configurations found with strict filters, attempting progressive fallback")

            # Fallback 1: Relax preferred brands requirement
            if user_profile.preferred_brands:
                logger.warning(f"[FALLBACK 1] Primary query failed, relaxing brand preferences. Original brands: {user_profile.preferred_brands}")
                fallback_configs = await self._try_fallback_query(
                    user_profile, max_recommendations, preferred_brands=None
                )
                if fallback_configs:
                    configs = fallback_configs
                    logger.info(f"[FALLBACK 1 SUCCESS] Found {len(configs)} configurations by removing brand preferences")

            # Fallback 2: Relax performance threshold
            if not configs:
                logger.warning(f"[FALLBACK 2] Still no results, relaxing performance threshold from {min_performance}")
                fallback_configs = await self._try_fallback_query(
                    user_profile, max_recommendations, relaxed_performance=True
                )
                if fallback_configs:
                    configs = fallback_configs
                    logger.info(f"[FALLBACK 2 SUCCESS] Found {len(configs)} configurations with reduced performance requirements")

            # Fallback 3: Relax budget margin
            if not configs:
                logger.warning(f"[FALLBACK 3] Still no results, expanding budget from ${user_profile.budget.min}-${user_profile.budget.max}")
                fallback_configs = await self._try_fallback_query(
                    user_profile, max_recommendations, expanded_budget=True
                )
                if fallback_configs:
                    configs = fallback_configs
                    logger.info(f"[FALLBACK 3 SUCCESS] Found {len(configs)} configurations with expanded budget range")

            # Fallback 4: Remove all optional constraints
            if not configs:
                logger.warning(f"[FALLBACK 4] Final attempt: removing all optional constraints")
                fallback_configs = await self._try_fallback_query(
                    user_profile, max_recommendations, no_constraints=True
                )
                if fallback_configs:
                    configs = fallback_configs
                    logger.info(f"[FALLBACK 4 SUCCESS] Found {len(configs)} configurations with all constraints removed")

        if not configs:
            logger.error("All fallback strategies failed - no configurations available in database")
            raise ValueError("No PC configurations available in the system")

        # Score and rank configurations with parallel processing
        logger.info(f"[SCORING] Starting parallel scoring of {len(configs)} configurations")
        scored_configs = []
        scoring_tasks = []

        # Create tasks for parallel scoring
        for config in configs:
            task = self._score_configuration(config, user_profile, safe_mode)
            scoring_tasks.append(task)

        # Execute scoring in parallel
        try:
            scoring_results = await asyncio.gather(*scoring_tasks, return_exceptions=True)

            for i, result in enumerate(scoring_results):
                if isinstance(result, Exception):
                    logger.warning(f"[SCORING ERROR] Failed for config {configs[i].get('_id')}: {result}")
                    continue

                if result:
                    scored_configs.append(result)
                    logger.debug(f"[SCORING] Config {result['name']}: ${result['total_price']} -> {result['confidence_score']:.1f}% match")

        except Exception as e:
            logger.error(f"[SCORING ERROR] Parallel scoring failed: {e}")
            # Fallback to sequential scoring
            for config in configs:
                score_data = await self._score_configuration(config, user_profile, safe_mode)
                if score_data:
                    scored_configs.append(score_data)
                    logger.debug(f"[SCORING FALLBACK] Config {score_data['name']}: ${score_data['total_price']} -> {score_data['confidence_score']:.1f}% match")

        # Sort by confidence score (descending) with safe sorting
        try:
            scored_configs.sort(key=lambda x: x.get('confidence_score', 0), reverse=True)
        except Exception as e:
            logger.error(f"Error sorting scored configs: {e}")
            # Fallback: return configs as-is if sorting fails
            pass

        # Take top recommendations with bounds checking
        try:
            top_recommendations = scored_configs[:max_recommendations] if scored_configs else []
        except Exception as e:
            logger.error(f"Error slicing top recommendations: {e}")
            top_recommendations = []

        # Check if we have any recommendations after scoring
        if not top_recommendations:
            logger.warning(f"No valid recommendations found after scoring {len(configs)} configurations")
            # Instead of failing, return the configurations with lowest scores but add warnings
            if scored_configs:
                # Return the least bad options with warnings
                top_recommendations = scored_configs[:max_recommendations]
                logger.info(f"Returning {len(top_recommendations)} configurations with low compatibility scores")
            else:
                raise ValueError("No PC configurations meet the minimum requirements after detailed scoring")

        # Log final selection with detailed reasoning
        logger.info(f"[SELECTION] Selected {len(top_recommendations)} top recommendations from {len(scored_configs)} scored candidates")
        for i, rec in enumerate(top_recommendations):
            fallback_note = f" [FALLBACK: {rec.get('fallback_type', 'none')}]" if rec.get('fallback_type') else ""
            logger.info(f"[SELECTION] #{i+1}: {rec['name']} (${rec['total_price']}) - {rec['confidence_score']:.1f}% match{fallback_note}")

            # Log detailed reasoning for each recommendation
            for reason in rec['match_reasons']:
                logger.debug(f"[REASONING] {rec['name']} - {reason['factor']}: {reason['weight']:.2f} weight - {reason['explanation']}")

            # Log trade-offs if any
            if rec.get('trade_offs'):
                for trade_off in rec['trade_offs']:
                    logger.debug(f"[TRADEOFF] {rec['name']} - {trade_off['type']}: {trade_off['impact']} - {trade_off['description']}")

        # Cache the results for 30 minutes
        await cache.set(cache_key, top_recommendations, ttl=1800)

        logger.info(f"Generated {len(top_recommendations)} recommendations for user: {user_profile.session_id}")
        return top_recommendations, False

    def _generate_purpose_explanation(self, purpose: str, score: float, suitability_scores: Dict[str, float]) -> str:
        """Generate detailed purpose matching explanation with rule-based logic"""
        try:
            purpose_descriptions = {
                'gaming': 'high-performance GPU and CPU for gaming',
                'creative': 'powerful GPU and CPU for creative work',
                'programming': 'reliable CPU and RAM for development',
                'office': 'balanced performance for productivity tasks',
                'general': 'versatile configuration for everyday use'
            }

            base_score = suitability_scores.get(purpose, 50)
            description = purpose_descriptions.get(purpose, 'general computing')

            if score >= 80:
                return f"Excellent match for {purpose} with {base_score}% suitability score, providing {description}"
            elif score >= 60:
                return f"Good match for {purpose} with {base_score}% suitability score, suitable for {description}"
            elif score >= 40:
                return f"Fair match for {purpose} with {base_score}% suitability score, adequate for {description}"
            else:
                return f"Basic compatibility for {purpose} with {base_score}% suitability score, may need upgrades for optimal {description}"

        except Exception as e:
            logger.error(f"Error generating purpose explanation for {purpose}: {e}")
            return f"Configuration suitable for {purpose} use"

    def _generate_budget_explanation(self, price: float, budget, fit_score: float) -> str:
        """Generate detailed budget fit explanation"""
        # Handle both dict and Pydantic model formats
        if hasattr(budget, 'min') and hasattr(budget, 'max'):
            budget_min = budget.min
            budget_max = budget.max
        elif isinstance(budget, dict):
            budget_min = budget.get('min', 0)
            budget_max = budget.get('max', 10000)
        else:
            budget_min = 0
            budget_max = 10000

        budget_center = (budget_min + budget_max) / 2

        if price < budget_min:
            return f"Price ${price} is below minimum budget of ${budget_min}"
        elif price > budget_max:
            return f"Price ${price} exceeds maximum budget of ${budget_max}"
        else:
            distance_from_center = abs(price - budget_center)
            budget_range = budget_max - budget_min

            if distance_from_center <= budget_range * 0.1:  # Within 10% of center
                return f"Price ${price} is optimally positioned within budget range (${budget_min}-${budget_max})"
            elif distance_from_center <= budget_range * 0.25:  # Within 25% of center
                return f"Price ${price} fits well within budget range (${budget_min}-${budget_max})"
            else:
                position = "higher" if price > budget_center else "lower"
                return f"Price ${price} is at the {position} end of budget range (${budget_min}-${budget_max})"

    def _generate_performance_explanation(self, required_level: str, performance_profile: Dict[str, float], purpose: str, score: float) -> str:
        """Generate detailed performance requirement explanation"""
        level_requirements = {
            'basic': {'description': 'basic computing tasks', 'min_score': 30},
            'standard': {'description': 'standard productivity and light gaming', 'min_score': 50},
            'high': {'description': 'demanding applications and gaming', 'min_score': 70},
            'professional': {'description': 'professional workloads and high-end gaming', 'min_score': 85}
        }

        req_info = level_requirements.get(required_level, level_requirements['standard'])
        overall_performance = performance_profile.get('overall_performance', 50)

        purpose_weights = {
            'gaming': 'GPU-focused performance',
            'creative': 'GPU and CPU balanced performance',
            'programming': 'CPU and RAM focused performance',
            'office': 'balanced general performance',
            'general': 'versatile overall performance'
        }

        performance_type = purpose_weights.get(purpose, 'overall performance')

        if score >= 90:
            return f"Exceeds {required_level} performance requirements ({overall_performance:.0f} overall score) for {req_info['description']}, providing excellent {performance_type}"
        elif score >= 75:
            return f"Meets {required_level} performance requirements ({overall_performance:.0f} overall score) for {req_info['description']}, with good {performance_type}"
        elif score >= 50:
            return f"Partially meets {required_level} performance requirements ({overall_performance:.0f} overall score) for {req_info['description']}, adequate {performance_type}"
        else:
            return f"Below {required_level} performance requirements ({overall_performance:.0f} overall score) for {req_info['description']}, limited {performance_type}"

    async def _try_fallback_query(
        self,
        user_profile: UserProfile,
        max_recommendations: int,
        preferred_brands: Optional[List[str]] = None,
        relaxed_performance: bool = False,
        expanded_budget: bool = False,
        no_constraints: bool = False
    ) -> List[Dict[str, Any]]:
        """Try a fallback query with relaxed constraints"""
        try:
            # Calculate adjusted thresholds
            purpose_thresholds = {
                'gaming': 60, 'creative': 55, 'programming': 50, 'office': 45, 'general': 40
            }
            performance_thresholds = {
                'basic': 30, 'standard': 45, 'high': 60, 'professional': 75
            }

            min_suitability = purpose_thresholds.get(user_profile.purpose, 40)
            min_performance = performance_thresholds.get(user_profile.performance_level, 40)

            # Apply relaxations
            if relaxed_performance:
                min_suitability = max(20, min_suitability - 20)
                min_performance = max(20, min_performance - 20)

            budget_min = user_profile.budget.min
            budget_max = user_profile.budget.max

            if expanded_budget:
                # Expand budget by 15%
                budget_range = budget_max - budget_min
                expansion = int(budget_range * 0.15)
                budget_min = max(0, budget_min - expansion)
                budget_max = budget_max + expansion

            # Use preferred_brands parameter if provided, otherwise use user_profile
            brands_to_use = preferred_brands if preferred_brands is not None else user_profile.preferred_brands

            # Build query
            purpose_field = f"suitability_scores.{user_profile.purpose}"

            match_conditions = {
                "suitability_scores": {"$exists": True},
                "performance_profile": {"$exists": True},
                "total_price": {"$gte": budget_min, "$lte": budget_max}
            }

            if not no_constraints:
                match_conditions[purpose_field] = {"$gte": min_suitability}
                match_conditions["performance_profile.overall_performance"] = {"$gte": min_performance}

            pipeline = [
                {"$match": match_conditions},
                {
                    "$addFields": {
                        "relevance_score": {
                            "$add": [
                                {"$multiply": [f"$suitability_scores.{user_profile.purpose}", 0.6]},
                                {"$multiply": ["$performance_profile.overall_performance", 0.4]}
                            ]
                        }
                    }
                },
                {"$sort": {"relevance_score": -1, "total_price": 1}},
                {"$limit": max_recommendations + 10}
            ]

            configs = await self.configs_collection.aggregate(pipeline).to_list(length=None)

            # If we found configs and this is a fallback, mark them as fallback results
            if configs:
                for config in configs:
                    config['_fallback_type'] = 'preferred_brands' if preferred_brands is None and user_profile.preferred_brands else \
                                             'relaxed_performance' if relaxed_performance else \
                                             'expanded_budget' if expanded_budget else \
                                             'no_constraints' if no_constraints else 'original'

            return configs

        except Exception as e:
            logger.warning(f"Fallback query failed: {e}")
            return []

    async def _score_configuration(
        self,
        config: Dict[str, Any],
        user_profile: UserProfile,
        safe_mode: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Score a PC configuration against user requirements with dynamic weighting

        Returns None if configuration doesn't meet minimum requirements
        """
        try:
            # Extract configuration data with safe defaults
            config_price = config.get('total_price', 0)
            if not isinstance(config_price, (int, float)) or config_price <= 0:
                logger.warning(f"Invalid config price: {config_price}, skipping config {config.get('_id')}")
                return None

            suitability_scores = config.get('suitability_scores', {})
            if not isinstance(suitability_scores, dict):
                logger.warning(f"Invalid suitability_scores: {suitability_scores}, skipping config {config.get('_id')}")
                return None

            performance_profile = config.get('performance_profile', {})
            if not isinstance(performance_profile, dict):
                logger.warning(f"Invalid performance_profile: {performance_profile}, skipping config {config.get('_id')}")
                return None

            # Check budget constraints
            if not self._check_budget_constraints(config_price, user_profile.budget):
                return None

            if safe_mode:
                # Safe mode: Use simple, predictable scoring with guaranteed results
                logger.debug(f"[SAFE SCORING] Using stable scoring for {config.get('name')}")

                # Simple equal weights for safe mode
                weights = {'purpose': 0.4, 'budget': 0.3, 'performance': 0.2, 'brand': 0.1}
                logger.debug(f"[SAFE WEIGHTS] Fixed weights for {config.get('name')}: purpose=0.4, budget=0.3, performance=0.2, brand=0.1")

                # Calculate base confidence score with safe mode logic
                confidence_score = 0
                match_reasons = []
                trade_offs = []

                # Purpose alignment with safe mode scoring (always returns a score)
                purpose_score = self._calculate_purpose_score_safe(
                    user_profile.purpose,
                    suitability_scores
                )
                confidence_score += purpose_score * weights['purpose']
                match_reasons.append(MatchReason(
                    factor="purpose_alignment",
                    weight=weights['purpose'],
                    explanation=f"Suitable for {user_profile.purpose} use (safe mode)"
                ))

                # Budget fit with safe mode (always returns reasonable score)
                budget_fit = self._calculate_budget_fit_safe(config_price, user_profile.budget)
                confidence_score += budget_fit * weights['budget']
                match_reasons.append(MatchReason(
                    factor="budget_fit",
                    weight=weights['budget'],
                    explanation=f"Price ${config_price} is within budget considerations (safe mode)"
                ))

                # Performance alignment with safe mode (guaranteed minimum score)
                performance_score = self._calculate_performance_score_safe(
                    user_profile.performance_level,
                    performance_profile
                )
                confidence_score += performance_score * weights['performance']
                match_reasons.append(MatchReason(
                    factor="performance_match",
                    weight=weights['performance'],
                    explanation=f"Meets {user_profile.performance_level} performance needs (safe mode)"
                ))

                # Brand preferences (optional bonus in safe mode)
                if user_profile.preferred_brands:
                    brand_bonus = await self._calculate_brand_preference_bonus(
                        config.get('components', []),
                        user_profile.preferred_brands
                    )
                    if brand_bonus > 0:
                        confidence_score += brand_bonus * weights['brand']
                        match_reasons.append(MatchReason(
                            factor="brand_preference",
                            weight=weights['brand'],
                            explanation=f"Includes some preferred brands (safe mode)"
                        ))
            else:
                # Normal mode: Use dynamic weights and complex scoring
                # Calculate dynamic weights based on user requirements
                weights = self._calculate_dynamic_weights(user_profile)
                logger.debug(f"[WEIGHTS] Dynamic weights for {config.get('name')}: purpose={weights['purpose']:.2f}, budget={weights['budget']:.2f}, performance={weights['performance']:.2f}, brand={weights['brand']:.2f}")

                # Calculate base confidence score
                confidence_score = 0
                match_reasons = []
                trade_offs = []

                # Purpose alignment (dynamic weight)
                purpose_score = self._calculate_purpose_score(
                    user_profile.purpose,
                    suitability_scores
                )
                if purpose_score > 0:
                    confidence_score += purpose_score * weights['purpose']
                    purpose_explanation = self._generate_purpose_explanation(
                        user_profile.purpose, purpose_score, suitability_scores
                    )
                    match_reasons.append(MatchReason(
                        factor="purpose_alignment",
                        weight=weights['purpose'],
                        explanation=purpose_explanation
                    ))

                # Budget fit (dynamic weight)
                budget_fit = self._calculate_budget_fit(config_price, user_profile.budget)
                confidence_score += budget_fit * weights['budget']
                budget_explanation = self._generate_budget_explanation(
                    config_price, user_profile.budget, budget_fit
                )
                match_reasons.append(MatchReason(
                    factor="budget_fit",
                    weight=weights['budget'],
                    explanation=budget_explanation
                ))

                # Performance alignment (dynamic weight, now includes purpose)
                performance_score = self._calculate_performance_score(
                    user_profile.performance_level,
                    performance_profile,
                    user_profile.purpose
                )
                confidence_score += performance_score * weights['performance']
                performance_explanation = self._generate_performance_explanation(
                    user_profile.performance_level, performance_profile, user_profile.purpose, performance_score
                )
                match_reasons.append(MatchReason(
                    factor="performance_match",
                    weight=weights['performance'],
                    explanation=performance_explanation
                ))

                # Brand preferences (dynamic weight)
                if user_profile.preferred_brands:
                    brand_bonus = await self._calculate_brand_preference_bonus(
                        config.get('components', []),
                        user_profile.preferred_brands
                    )
                    if brand_bonus > 0:
                        brand_weight = min(brand_bonus * 0.1, weights['brand'])
                        confidence_score += brand_bonus * brand_weight
                        match_reasons.append(MatchReason(
                            factor="brand_preference",
                            weight=brand_weight,
                            explanation=f"Includes preferred brands: {', '.join(user_profile.preferred_brands)}"
                        ))

            # Check for trade-offs
            trade_offs = self._identify_trade_offs(
                config_price,
                user_profile.budget,
                performance_profile,
                user_profile.performance_level,
                user_profile.purpose
            )

            # Ensure confidence score is within bounds
            confidence_score = max(0, min(100, confidence_score))

            # Log detailed scoring breakdown
            logger.debug(f"[SCORE BREAKDOWN] {config.get('name')} (${config_price}): Final={confidence_score:.1f}% | Purpose: {purpose_score:.1f} * {weights['purpose']:.2f} = {purpose_score * weights['purpose']:.1f} | Budget: {budget_fit:.1f} * {weights['budget']:.2f} = {budget_fit * weights['budget']:.1f} | Performance: {performance_score:.1f} * {weights['performance']:.2f} = {performance_score * weights['performance']:.1f}")

            # Log high-confidence matches
            if confidence_score >= 80:
                logger.info(f"[HIGH CONFIDENCE] {config.get('name')} (${config_price}) scored {confidence_score:.1f}% match")

            # Get component details for display
            component_summaries = await self._get_component_summaries(
                config.get('components', [])
            )

            # Add fallback explanation if this is a fallback result
            fallback_type = config.get('_fallback_type')
            if fallback_type:
                if fallback_type == 'preferred_brands':
                    match_reasons.append(MatchReason(
                        factor="fallback_note",
                        weight=0.0,
                        explanation="Configuration shown because preferred brands requirement was relaxed to find suitable options"
                    ))
                elif fallback_type == 'relaxed_performance':
                    match_reasons.append(MatchReason(
                        factor="fallback_note",
                        weight=0.0,
                        explanation="Configuration shown with relaxed performance requirements to provide options"
                    ))
                elif fallback_type == 'expanded_budget':
                    match_reasons.append(MatchReason(
                        factor="fallback_note",
                        weight=0.0,
                        explanation="Configuration shown with expanded budget range to find suitable options"
                    ))
                elif fallback_type == 'no_constraints':
                    match_reasons.append(MatchReason(
                        factor="fallback_note",
                        weight=0.0,
                        explanation="Configuration shown with all optional constraints removed - consider as general recommendation"
                    ))

            return {
                'configuration_id': str(config['_id']),
                'name': config.get('name', 'Unnamed Configuration'),
                'total_price': config_price,
                'confidence_score': round(confidence_score, 1),
                'match_reasons': [reason.dict() for reason in match_reasons],
                'trade_offs': [trade_off.dict() for trade_off in trade_offs],
                'components': component_summaries,
                'fallback_type': fallback_type
            }

        except Exception as e:
            logger.error(f"Error scoring configuration {config.get('_id')}: {e}")
            return None

    def _check_budget_constraints(self, price: float, budget: Dict[str, float]) -> bool:
        """Check if configuration fits within budget constraints"""
        return budget.min <= price <= budget.max

    def _calculate_purpose_score(self, purpose: str, suitability_scores: Dict[str, float]) -> float:
        """Calculate how well configuration matches user's purpose with dynamic weighting"""
        purpose_mapping = {
            'gaming': 'gaming',
            'office': 'office',
            'creative': 'creative',
            'programming': 'programming',
            'general': 'general'
        }

        purpose_key = purpose_mapping.get(purpose, 'general')
        base_score = suitability_scores.get(purpose_key, 50)
        
        # Dynamic weighting based on purpose specificity
        purpose_weights = {
            'gaming': 1.2,    # Gaming requires specific GPU/CPU
            'creative': 1.15, # Creative work needs good GPU/CPU
            'programming': 1.0, # Programming is more flexible
            'office': 0.9,    # Office work is least demanding
            'general': 1.0    # General purpose
        }
        
        weight = purpose_weights.get(purpose, 1.0)
        return min(100, base_score * weight)

    def _calculate_budget_fit(self, price: float, budget) -> float:
        """Calculate budget fit score (0-100) with dynamic weighting based on budget tightness"""
        try:
            # Validate inputs
            if not isinstance(price, (int, float)) or price < 0:
                return 0

            # Handle both dict and Pydantic model formats
            if hasattr(budget, 'min') and hasattr(budget, 'max'):
                budget_min = budget.min
                budget_max = budget.max
            elif isinstance(budget, dict):
                budget_min = budget.get('min', 0)
                budget_max = budget.get('max', 0)
            else:
                return 0

            if budget_min >= budget_max or budget_min < 0 or budget_max < 0:
                return 0

            budget_range = budget_max - budget_min

            # Dynamic weighting based on budget range tightness
            if budget_range <= 0:
                return 100 if price == budget_min else 50

            # Calculate budget tightness factor (narrower range = more critical)
            tightness_factor = max(0.5, min(2.0, 1000 / budget_range))  # Normalize for typical budget ranges

            # Calculate how centered the price is in the budget range
            center = (budget_min + budget_max) / 2
            distance_from_center = abs(price - center)
            max_distance = budget_range / 2

            # Prevent division by zero
            if max_distance <= 0:
                return 50

            # Score decreases as price moves away from budget center, weighted by tightness
            fit_score = max(0, 100 * (1 - distance_from_center / max_distance) * tightness_factor)

            # Add bonus for being close to budget limits (value-conscious choices)
            if abs(price - budget_min) < budget_range * 0.1:  # Within 10% of minimum
                fit_score = min(100, fit_score + 15)
            elif abs(price - budget_max) < budget_range * 0.1:  # Within 10% of maximum
                fit_score = min(100, fit_score + 10)

            return fit_score

        except Exception as e:
            logger.error(f"Error calculating budget fit for price {price}, budget {budget}: {e}")
            return 50  # Return neutral score on error

    def _calculate_dynamic_weights(self, user_profile: UserProfile) -> Dict[str, float]:
        """Calculate dynamic weights for scoring factors based on user requirements"""
        try:
            # Base weights
            weights = {
                'purpose': 0.4,
                'budget': 0.3,
                'performance': 0.2,
                'brand': 0.1
            }

            # Validate user profile
            if not hasattr(user_profile, 'budget') or not user_profile.budget:
                logger.warning("User profile missing budget, using default weights")
                return weights

            # Adjust weights based on budget range tightness
            budget_range = user_profile.budget.max - user_profile.budget.min
            if budget_range < 500:  # Very tight budget
                weights['budget'] = 0.4  # Increase budget importance
                weights['purpose'] = 0.3
                weights['performance'] = 0.2
                weights['brand'] = 0.1
            elif budget_range > 2000:  # Flexible budget
                weights['budget'] = 0.2  # Reduce budget importance
                weights['purpose'] = 0.4
                weights['performance'] = 0.3
                weights['brand'] = 0.1

            # Adjust weights based on performance level
            performance_weights = {
                'basic': 0.15,
                'standard': 0.2,
                'high': 0.25,
                'professional': 0.3
            }
            weights['performance'] = performance_weights.get(getattr(user_profile, 'performance_level', 'standard'), 0.2)

            # Adjust weights based on purpose
            purpose_weights = {
                'gaming': {'purpose': 0.45, 'performance': 0.3, 'budget': 0.2, 'brand': 0.05},
                'creative': {'purpose': 0.4, 'performance': 0.3, 'budget': 0.2, 'brand': 0.1},
                'programming': {'purpose': 0.35, 'performance': 0.3, 'budget': 0.25, 'brand': 0.1},
                'office': {'purpose': 0.3, 'performance': 0.2, 'budget': 0.4, 'brand': 0.1},
                'general': {'purpose': 0.35, 'performance': 0.25, 'budget': 0.3, 'brand': 0.1}
            }

            if hasattr(user_profile, 'purpose') and user_profile.purpose in purpose_weights:
                purpose_weight = purpose_weights[user_profile.purpose]
                weights.update(purpose_weight)

            # Normalize weights to sum to 1.0
            total_weight = sum(weights.values())
            if total_weight > 0:
                for key in weights:
                    weights[key] = weights[key] / total_weight
            else:
                logger.warning("Total weight is 0, using default weights")
                return {
                    'purpose': 0.4,
                    'budget': 0.3,
                    'performance': 0.2,
                    'brand': 0.1
                }

            return weights

        except Exception as e:
            logger.error(f"Error calculating dynamic weights for user profile: {e}")
            return {
                'purpose': 0.4,
                'budget': 0.3,
                'performance': 0.2,
                'brand': 0.1
            }

    def _calculate_performance_score(self, required_level: str, performance_profile: Dict[str, float], purpose: str = 'general') -> float:
        """Calculate performance alignment score with dynamic weighting based on use case"""
        try:
            level_mapping = {
                'basic': 30,
                'standard': 50,
                'high': 70,
                'professional': 85
            }

            required_score = level_mapping.get(required_level, 50)
            overall_performance = performance_profile.get('overall_performance', 50)

            # Validate inputs
            if not isinstance(performance_profile, dict):
                return 50

            # Dynamic component weighting based on purpose
            purpose_weights = {
                'gaming': {
                    'gpu': 0.5,  # GPU most important for gaming
                    'cpu': 0.3,
                    'ram': 0.15,
                    'storage': 0.05
                },
                'creative': {
                    'gpu': 0.4,  # GPU important for creative work
                    'cpu': 0.35,
                    'ram': 0.2,
                    'storage': 0.05
                },
                'programming': {
                    'cpu': 0.4,  # CPU most important for programming
                    'ram': 0.3,
                    'gpu': 0.2,
                    'storage': 0.1
                },
                'office': {
                    'cpu': 0.3,
                    'ram': 0.3,
                    'gpu': 0.2,
                    'storage': 0.2
                },
                'general': {
                    'cpu': 0.3,
                    'gpu': 0.3,
                    'ram': 0.2,
                    'storage': 0.2
                }
            }

            # Calculate weighted performance score based on purpose
            weighted_performance = 0
            weights = purpose_weights.get(purpose, purpose_weights['general'])

            for component, weight in weights.items():
                component_score = performance_profile.get(f'{component}_performance', 50)
                if isinstance(component_score, (int, float)):
                    weighted_performance += component_score * weight

            # Score based on how well weighted performance meets requirements
            if weighted_performance >= required_score:
                return 100
            elif weighted_performance >= required_score * 0.8:  # Within 80%
                return 75
            elif weighted_performance >= required_score * 0.6:  # Within 60%
                return 50
            else:
                return 25

        except Exception as e:
            logger.error(f"Error calculating performance score for level {required_level}, purpose {purpose}: {e}")
            return 50  # Return neutral score on error

    async def _calculate_brand_preference_bonus(
        self,
        components: List[Dict[str, Any]],
        preferred_brands: List[str]
    ) -> float:
        """Calculate bonus for including preferred brands"""
        if not preferred_brands:
            return 0

        # Get component details
        component_ids = [comp['component_id'] for comp in components if 'component_id' in comp]
        if not component_ids:
            return 0

        # Query components to get brands
        query = {"_id": {"$in": component_ids}}
        component_docs = await self.components_collection.find(query).to_list(length=None)

        matching_brands = 0
        total_components = len(component_docs)

        for doc in component_docs:
            if doc.get('brand', '').upper() in [b.upper() for b in preferred_brands]:
                matching_brands += 1

        if total_components == 0:
            return 0

        # Return percentage of components that match preferred brands
        return (matching_brands / total_components) * 100

    def _calculate_purpose_score_safe(self, purpose: str, suitability_scores: Dict[str, float]) -> float:
        """Calculate purpose score for safe mode - always returns a reasonable score"""
        try:
            purpose_mapping = {
                'gaming': 'gaming',
                'office': 'office',
                'creative': 'creative',
                'programming': 'programming',
                'general': 'general'
            }

            purpose_key = purpose_mapping.get(purpose, 'general')
            base_score = suitability_scores.get(purpose_key, 50)

            # In safe mode, ensure minimum score of 60 for any purpose
            return max(60, min(100, base_score))

        except Exception as e:
            logger.error(f"Error in safe mode purpose scoring for {purpose}: {e}")
            return 70  # Safe fallback score

    def _calculate_budget_fit_safe(self, price: float, budget) -> float:
        """Calculate budget fit for safe mode - always returns reasonable score"""
        try:
            # Handle both dict and Pydantic model formats
            if hasattr(budget, 'min') and hasattr(budget, 'max'):
                budget_min = budget.min
                budget_max = budget.max
            elif isinstance(budget, dict):
                budget_min = budget.get('min', 0)
                budget_max = budget.get('max', 10000)
            else:
                budget_min = 0
                budget_max = 10000

            # In safe mode, be very lenient with budget
            if price < budget_min:
                return 70  # Slightly below budget is acceptable
            elif price > budget_max:
                return 60  # Slightly above budget is still okay
            else:
                # Within budget - good score
                budget_range = budget_max - budget_min
                if budget_range == 0:
                    return 85

                center = (budget_min + budget_max) / 2
                distance_from_center = abs(price - center)
                max_distance = budget_range / 2

                # More lenient scoring in safe mode
                fit_score = max(70, 100 * (1 - distance_from_center / max_distance))
                return fit_score

        except Exception as e:
            logger.error(f"Error in safe mode budget fit for price {price}: {e}")
            return 75  # Safe fallback score

    def _calculate_performance_score_safe(self, required_level: str, performance_profile: Dict[str, float]) -> float:
        """Calculate performance score for safe mode - guaranteed minimum score"""
        try:
            level_mapping = {
                'basic': 40,      # Lower threshold in safe mode
                'standard': 50,
                'high': 60,
                'professional': 70
            }

            required_score = level_mapping.get(required_level, 50)
            overall_performance = performance_profile.get('overall_performance', 50)

            # In safe mode, ensure minimum score of 65
            if overall_performance >= required_score:
                return max(85, min(100, overall_performance))
            elif overall_performance >= required_score * 0.7:  # Within 70%
                return 75
            elif overall_performance >= required_score * 0.5:  # Within 50%
                return 70
            else:
                return 65  # Minimum guaranteed score in safe mode

        except Exception as e:
            logger.error(f"Error in safe mode performance scoring for level {required_level}: {e}")
            return 70  # Safe fallback score

    def _identify_trade_offs(
        self,
        price: float,
        budget,
        performance_profile: Dict[str, float],
        required_level: str,
        purpose: str = 'general'
    ) -> List[TradeOff]:
        """Identify potential trade-offs with detailed, rule-based explanations"""
        trade_offs = []

        # Handle both dict and Pydantic model formats
        if hasattr(budget, 'min') and hasattr(budget, 'max'):
            budget_min = budget.min
            budget_max = budget.max
        elif isinstance(budget, dict):
            budget_min = budget.get('min', 0)
            budget_max = budget.get('max', 10000)
        else:
            budget_min = 0
            budget_max = 10000

        # Budget trade-offs with quantitative analysis
        budget_range = budget_max - budget_min
        budget_center = (budget_min + budget_max) / 2

        # Dynamic threshold based on budget range tightness
        threshold_factor = max(0.1, min(0.3, 500 / max(budget_range, 1)))  # 10-30% range

        if price > budget_center * (1 + threshold_factor):
            excess_percentage = ((price - budget_center) / budget_center) * 100
            trade_offs.append(TradeOff(
                type="budget",
                impact="negative",
                description=f"Price exceeds budget center by {excess_percentage:.0f}% - may strain budget allocation for peripherals or future upgrades"
            ))
        elif price < budget_min * 1.1:
            trade_offs.append(TradeOff(
                type="performance",
                impact="neutral",
                description="Budget-optimized choice provides core functionality but may require component upgrades for demanding tasks"
            ))

        # Performance trade-offs with detailed analysis
        overall_performance = performance_profile.get('overall_performance', 50)
        level_requirements = {'basic': 30, 'standard': 50, 'high': 70, 'professional': 85}
        required_min = level_requirements.get(required_level, 50)

        # Dynamic performance threshold based on required level and purpose
        purpose_multiplier = {'gaming': 1.0, 'creative': 0.95, 'programming': 0.9, 'office': 0.85, 'general': 0.9}
        performance_threshold = required_min * purpose_multiplier.get(purpose, 0.9)

        if overall_performance < performance_threshold:
            deficit = performance_threshold - overall_performance
            trade_offs.append(TradeOff(
                type="performance",
                impact="negative",
                description=f"Overall performance ({overall_performance:.0f}%) falls {deficit:.0f} points below {required_level} threshold for {purpose} use - may experience slowdowns in demanding applications"
            ))

        # Component-specific trade-offs with purpose context
        cpu_performance = performance_profile.get('cpu_performance', 50)
        gpu_performance = performance_profile.get('gpu_performance', 50)
        ram_performance = performance_profile.get('ram_performance', 50)

        # CPU analysis based on purpose
        cpu_threshold = required_min * {'gaming': 0.8, 'creative': 0.85, 'programming': 0.9, 'office': 0.7, 'general': 0.75}.get(purpose, 0.75)
        if cpu_performance < cpu_threshold:
            purpose_cpu_needs = {
                'gaming': 'gaming and multitasking',
                'creative': 'rendering and design work',
                'programming': 'compilation and development tasks',
                'office': 'productivity applications',
                'general': 'everyday computing'
            }
            trade_offs.append(TradeOff(
                type="cpu",
                impact="negative",
                description=f"CPU performance ({cpu_performance:.0f}%) may bottleneck {purpose_cpu_needs.get(purpose, 'general tasks')} - consider upgrade for smoother experience"
            ))

        # GPU analysis based on purpose
        gpu_threshold = required_min * {'gaming': 0.9, 'creative': 0.9, 'programming': 0.6, 'office': 0.5, 'general': 0.7}.get(purpose, 0.7)
        if gpu_performance < gpu_threshold:
            purpose_gpu_needs = {
                'gaming': 'gaming at target resolutions/frame rates',
                'creative': 'GPU-accelerated design and editing',
                'programming': 'GPU computing tasks',
                'office': 'basic graphics tasks',
                'general': 'casual gaming and media'
            }
            trade_offs.append(TradeOff(
                type="gpu",
                impact="negative",
                description=f"GPU performance ({gpu_performance:.0f}%) may limit {purpose_gpu_needs.get(purpose, 'graphics tasks')} - upgrade recommended for optimal visual performance"
            ))

        # RAM analysis for memory-intensive tasks
        ram_threshold = required_min * {'gaming': 0.7, 'creative': 0.8, 'programming': 0.8, 'office': 0.6, 'general': 0.7}.get(purpose, 0.7)
        if ram_performance < ram_threshold:
            purpose_ram_needs = {
                'gaming': 'game loading and multitasking',
                'creative': 'large file handling and rendering',
                'programming': 'development environment and compilation',
                'office': 'multiple application usage',
                'general': 'web browsing and media consumption'
            }
            trade_offs.append(TradeOff(
                type="memory",
                impact="negative",
                description=f"Memory performance ({ram_performance:.0f}%) may constrain {purpose_ram_needs.get(purpose, 'multitasking')} - additional RAM recommended for better performance"
            ))

        return trade_offs

    async def _get_component_summaries(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get summary information for configuration components"""
        if not components:
            return []

        component_ids = [comp['component_id'] for comp in components if 'component_id' in comp]
        if not component_ids:
            return []

        # Create cache key based on component IDs
        cache_key = generate_cache_key("component_summaries", sorted(component_ids))

        # Try cache first
        cached_result = await cache.get(cache_key)
        if cached_result:
            return cached_result

        # Query components
        from bson import ObjectId
        object_ids = []
        for cid in component_ids:
            try:
                object_ids.append(ObjectId(cid))
            except Exception:
                pass
        query = {"_id": {"$in": object_ids}} if object_ids else {"_id": {"$in": []}}
        component_docs = await self.components_collection.find(query).to_list(length=None)

        summaries = []
        for comp in components:
            comp_id = comp.get('component_id')
            comp_doc = next((doc for doc in component_docs if str(doc['_id']) == comp_id), None)

            if comp_doc:
                summaries.append({
                    'id': comp_id,
                    'type': comp_doc.get('type', 'unknown'),
                    'name': comp_doc.get('name', 'Unknown Component'),
                    'brand': comp_doc.get('brand', 'Unknown Brand'),
                    'price': comp_doc.get('price', {}).get('amount', 0)
                })

        # Cache the result
        await cache.set(cache_key, summaries, 1800)  # 30 minutes

        return summaries


# Global recommendation engine instance
recommendation_engine = RecommendationEngine()
