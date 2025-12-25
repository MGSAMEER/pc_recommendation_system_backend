#!/usr/bin/env python3
"""
Database indexes setup script for PC Recommendation System
Creates optimized indexes for performance
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import connect_to_mongo, get_database


async def setup_indexes():
    """Create database indexes for optimal performance"""
    print("Setting up database indexes...")

    try:
        # Connect to database
        await connect_to_mongo()
        db = await get_database()

        # User collection indexes
        print("Creating user collection indexes...")
        await db.users.create_index("email", unique=True)
        await db.users.create_index("is_active")
        await db.users.create_index("created_at")
        await db.users.create_index("last_login")
        await db.users.create_index([("is_active", 1), ("last_login", -1)])

        # User sessions indexes
        print("Creating user sessions collection indexes...")
        await db.user_sessions.create_index("user_id")
        await db.user_sessions.create_index("session_token", unique=True)
        await db.user_sessions.create_index("refresh_token", unique=True)
        await db.user_sessions.create_index("expires_at", expireAfterSeconds=0)
        await db.user_sessions.create_index([("user_id", 1), ("is_active", 1)])
        await db.user_sessions.create_index("last_activity")

        # PC Recommendations indexes
        print("Creating PC recommendations collection indexes...")
        await db.pc_recommendations.create_index("user_id")
        await db.pc_recommendations.create_index("session_id")
        await db.pc_recommendations.create_index("created_at")
        await db.pc_recommendations.create_index("expires_at", expireAfterSeconds=0)
        await db.pc_recommendations.create_index([("user_id", 1), ("created_at", -1)])
        await db.pc_recommendations.create_index([("session_id", 1), ("created_at", -1)])

        # Components indexes
        print("Creating components collection indexes...")
        await db.components.create_index("id", unique=True)
        await db.components.create_index("type")
        await db.components.create_index("brand")
        await db.components.create_index("price")
        await db.components.create_index("performance_score")
        await db.components.create_index([("type", 1), ("brand", 1)])
        await db.components.create_index([("type", 1), ("performance_score", -1)])
        await db.components.create_index([("brand", 1), ("price", 1)])

        # PC Configurations indexes
        print("Creating PC configurations collection indexes...")
        await db.pc_configurations.create_index("id", unique=True)
        await db.pc_configurations.create_index("purpose")
        await db.pc_configurations.create_index("performance_level")
        await db.pc_configurations.create_index("total_price")
        await db.pc_configurations.create_index([("purpose", 1), ("performance_level", 1)])
        await db.pc_configurations.create_index([("total_price", 1), ("performance_level", 1)])

        # Feedback analytics indexes
        print("Creating feedback analytics collection indexes...")
        await db.feedback_analytics.create_index([("recommendation_id", 1), ("timestamp", -1)])
        await db.feedback_analytics.create_index("helpful")
        await db.feedback_analytics.create_index("rating")
        await db.feedback_analytics.create_index([("user_id", 1), ("timestamp", -1)])

        # User feedback indexes (embedded in recommendations)
        print("Creating user feedback indexes...")
        await db.pc_recommendations.create_index("user_feedback.rating")
        await db.pc_recommendations.create_index("user_feedback.helpful")
        await db.pc_recommendations.create_index("user_feedback.submitted_at")

        # Audit logs indexes
        print("Creating audit logs collection indexes...")
        await db.audit_logs.create_index("user_id")
        await db.audit_logs.create_index("action")
        await db.audit_logs.create_index("resource_type")
        await db.audit_logs.create_index("timestamp")
        await db.audit_logs.create_index("severity")
        await db.audit_logs.create_index([("user_id", 1), ("timestamp", -1)])
        await db.audit_logs.create_index([("action", 1), ("timestamp", -1)])
        await db.audit_logs.create_index([("severity", 1), ("timestamp", -1)])

        # Analytics cache indexes
        print("Creating analytics cache collection indexes...")
        await db.analytics_cache.create_index("key", unique=True)
        await db.analytics_cache.create_index("expires_at", expireAfterSeconds=0)

        print("All database indexes created successfully!")
        print("\nIndex Summary:")
        print("- User authentication: email uniqueness, active status, login tracking")
        print("- Sessions: token validation, expiration, activity tracking")
        print("- Recommendations: user lookup, expiration, time-based queries")
        print("- Components: type/brand filtering, price/performance sorting")
        print("- Configurations: purpose/level filtering, price optimization")
        print("- Analytics: time-series queries, user behavior tracking")
        print("- Audit: compliance logging, security event tracking")

        return True

    except Exception as e:
        print(f"ERROR: Failed to setup indexes: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main execution"""
    success = await setup_indexes()
    if success:
        print("\n🎉 Database indexes setup completed successfully!")
        print("The database is now optimized for PC Recommendation System performance.")
        return 0
    else:
        print("\n❌ Database indexes setup failed.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
