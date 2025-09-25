#!/usr/bin/env python3
"""Quick migration to fix order_id field size in production."""

import os
import sys
from sqlalchemy import create_engine, text

def run_migration():
    """Run the database migration to fix order_id field size."""

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False

    # Convert postgresql:// to postgresql+pg8000:// for pg8000 driver
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+pg8000://', 1)

    print(f"🔗 Connecting to database...")

    try:
        engine = create_engine(database_url)

        with engine.connect() as conn:
            print("🔄 Updating executions.order_id column size to 500 characters...")

            # Check current column size first
            result = conn.execute(text("""
                SELECT character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'executions' AND column_name = 'order_id';
            """))

            current_length = result.fetchone()
            if current_length:
                print(f"📏 Current order_id field size: {current_length[0]} characters")

                if current_length[0] >= 500:
                    print("✅ Field already has correct size, no migration needed!")
                    return True

            # Update column size
            conn.execute(text("""
                ALTER TABLE executions
                ALTER COLUMN order_id TYPE VARCHAR(500);
            """))

            conn.commit()
            print("✅ Migration completed successfully!")
            print("💾 order_id field is now 500 characters")
            return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if "does not exist" in str(e):
            print("💡 This might be normal if the table structure is different")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)