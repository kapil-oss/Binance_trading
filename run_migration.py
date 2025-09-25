"""Run database migration during app startup."""

import asyncio
from migrate_order_id import migrate_order_id_column

async def run_migration():
    """Run the database migration."""
    print("🔄 Running database migration...")
    try:
        migrate_order_id_column()
        print("✅ Migration completed successfully!")
    except Exception as e:
        print(f"⚠️ Migration failed (this might be normal if already migrated): {e}")

if __name__ == "__main__":
    asyncio.run(run_migration())