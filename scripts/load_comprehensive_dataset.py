#!/usr/bin/env python3
"""
Comprehensive Dataset Loader for PC Recommendation System
Loads the complete dataset from dataset.py into MongoDB
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Add dataset path to sys.path
dataset_path = Path("c:/Users/Sameer/Desktop")
sys.path.insert(0, str(dataset_path))

try:
    from dataset import (
        get_all_components, get_all_configurations,
        get_all_cpus, get_all_gpus, get_all_ram,
        get_all_storage, get_all_motherboards,
        get_all_psus, get_all_cases
    )
    print("Successfully imported dataset functions")
except ImportError as e:
    print(f"ERROR: Failed to import dataset: {e}")
    print("Make sure dataset.py is available at c:/Users/Sameer/Desktop/dataset.py")
    sys.exit(1)

from app.core.database import get_database, connect_to_mongo
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatasetLoader:
    """Loads comprehensive PC component dataset into MongoDB"""

    def __init__(self):
        self.db = None

    async def initialize(self):
        """Initialize database connection"""
        logger.info("Initializing database connection...")
        await connect_to_mongo()
        self.db = await get_database()
        logger.info("Database connection established")

    async def clear_existing_data(self):
        """Clear existing data from all collections"""
        logger.info("Clearing existing data...")

        collections_to_clear = [
            'components',
            'pc_configurations',
            'analytics_cache',
            'feedback_analytics'
        ]

        for collection_name in collections_to_clear:
            try:
                collection = self.db[collection_name]
                result = await collection.delete_many({})
                logger.info(f"  Cleared {result.deleted_count} documents from {collection_name}")
            except Exception as e:
                logger.warning(f"  Failed to clear {collection_name}: {e}")

    async def load_components(self):
        """Load all PC components into the database"""
        logger.info("Loading PC components...")

        components = get_all_components()

        # Add metadata to each component
        for component in components:
            component.update({
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'is_active': True,
                'stock_status': 'available',
                'last_checked': datetime.utcnow()
            })

        # Insert components
        if components:
            result = await self.db.components.insert_many(components)
            logger.info(f"[OK] Inserted {len(result.inserted_ids)} components")

            # Create indexes for better performance
            await self.db.components.create_index('id', unique=True)
            await self.db.components.create_index('type')
            await self.db.components.create_index('brand')
            await self.db.components.create_index('price')
            await self.db.components.create_index([('type', 1), ('brand', 1)])
            logger.info("[OK] Created component indexes")
        else:
            logger.warning("[WARN] No components to load")

    async def load_configurations(self):
        """Load PC configurations into the database"""
        logger.info("Loading PC configurations...")

        configurations = get_all_configurations()

        # Add metadata and resolve component references
        for config in configurations:
            # Resolve component IDs to full component objects
            resolved_components = {}
            for comp_type, comp_id in config['components'].items():
                if comp_id:
                    component = await self.db.components.find_one({'id': comp_id})
                    if component:
                        resolved_components[comp_type] = {
                            'id': component['id'],
                            'name': component['name'],
                            'brand': component['brand'],
                            'price': component['price']
                        }
                    else:
                        logger.warning(f"Component {comp_id} not found for config {config['id']}")
                        resolved_components[comp_type] = None
                else:
                    resolved_components[comp_type] = None

            config.update({
                'resolved_components': resolved_components,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'is_active': True,
                'popularity_score': 0,
                'user_ratings': [],
                'compatibility_score': config.get('compatibility_score', 85),
                'value_score': config.get('value_score', 80)
            })

        # Insert configurations
        if configurations:
            result = await self.db.pc_configurations.insert_many(configurations)
            logger.info(f"[OK] Inserted {len(result.inserted_ids)} PC configurations")

            # Create indexes
            await self.db.pc_configurations.create_index('id', unique=True)
            await self.db.pc_configurations.create_index('purpose')
            await self.db.pc_configurations.create_index('performance_level')
            await self.db.pc_configurations.create_index('total_price')
            logger.info("[OK] Created configuration indexes")
        else:
            logger.warning("[WARN] No configurations to load")

    async def create_analytics_collections(self):
        """Create analytics collections with proper indexes"""
        logger.info("Setting up analytics collections...")

        # Feedback analytics collection
        await self.db.feedback_analytics.create_index([('recommendation_id', 1), ('timestamp', -1)])
        await self.db.feedback_analytics.create_index('helpful')
        await self.db.feedback_analytics.create_index('rating')

        # Cache collection for performance
        await self.db.analytics_cache.create_index('key', unique=True)
        await self.db.analytics_cache.create_index('expires_at', expireAfterSeconds=0)

        logger.info("[OK] Analytics collections setup complete")

    async def validate_data_integrity(self):
        """Validate that loaded data is consistent"""
        logger.info("Validating data integrity...")

        # Check component counts
        component_count = await self.db.components.count_documents({})
        logger.info(f"  Components in database: {component_count}")

        # Check configuration counts
        config_count = await self.db.pc_configurations.count_documents({})
        logger.info(f"  Configurations in database: {config_count}")

        # Validate component references in configurations
        configs = await self.db.pc_configurations.find({}).to_list(length=None)
        broken_refs = 0

        for config in configs:
            for comp_type, comp_data in config.get('resolved_components', {}).items():
                if comp_data and comp_data.get('id'):
                    component_exists = await self.db.components.find_one({'id': comp_data['id']})
                    if not component_exists:
                        logger.warning(f"  Broken reference: {comp_data['id']} in config {config['id']}")
                        broken_refs += 1

        if broken_refs == 0:
            logger.info("[OK] All component references are valid")
        else:
            logger.warning(f"[WARN] Found {broken_refs} broken component references")

        # Summary
        logger.info("Data integrity validation complete")
        return {
            'components_loaded': component_count,
            'configurations_loaded': config_count,
            'broken_references': broken_refs
        }

    async def generate_sample_queries(self):
        """Generate sample queries to demonstrate the dataset"""
        logger.info("Generating sample queries...")

        # Sample queries
        samples = {
            'total_components': await self.db.components.count_documents({}),
            'gpu_count': await self.db.components.count_documents({'type': 'gpu'}),
            'gaming_configs': await self.db.pc_configurations.count_documents({'purpose': 'gaming'}),
            'price_range_count': len(await self.db.components.find(
                {'price': {'$gte': 100, '$lte': 300}}
            ).to_list(length=None))
        }

        # Get average CPU price
        avg_cpu_pipeline = [
            {'$match': {'type': 'cpu'}},
            {'$group': {'_id': None, 'avg_price': {'$avg': '$price'}}}
        ]
        avg_cpu_result = await self.db.components.aggregate(avg_cpu_pipeline).to_list(length=1)
        avg_cpu_price = avg_cpu_result[0]['avg_price'] if avg_cpu_result else 0

        logger.info("Sample dataset statistics:")
        logger.info(f"  Total components: {samples['total_components']}")
        logger.info(f"  GPU components: {samples['gpu_count']}")
        logger.info(".2f")
        logger.info(f"  Gaming configurations: {samples['gaming_configs']}")
        logger.info(f"  Components $100-$300: {samples['price_range_count']}")

    async def load_comprehensive_dataset(self):
        """Load the complete dataset"""
        logger.info("[START] Starting comprehensive dataset loading...")
        logger.info("=" * 60)

        try:
            # Initialize
            await self.initialize()

            # Clear existing data
            await self.clear_existing_data()

            # Load data
            await self.load_components()
            await self.load_configurations()
            await self.create_analytics_collections()

            # Validate
            validation_results = await self.validate_data_integrity()

            # Generate samples
            await self.generate_sample_queries()

            logger.info("=" * 60)
            logger.info("[OK] Dataset loading completed successfully!")
            logger.info(f"[DATA] Loaded {validation_results['components_loaded']} components")
            logger.info(f"[CONFIG] Loaded {validation_results['configurations_loaded']} configurations")

            if validation_results['broken_references'] == 0:
                logger.info("[TARGET] All data references are valid")
            else:
                logger.warning(f"[WARN] {validation_results['broken_references']} broken references found")

            return True

        except Exception as e:
            logger.error(f"[ERROR] Dataset loading failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


async def main():
    """Main execution function"""
    loader = DatasetLoader()
    success = await loader.load_comprehensive_dataset()

    if success:
        logger.info("\n[SUCCESS] Dataset successfully loaded into MongoDB!")
        logger.info("You can now use the enhanced PC recommendation system.")
        return 0
    else:
        logger.error("\n[ERROR] Dataset loading failed. Check the logs above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
