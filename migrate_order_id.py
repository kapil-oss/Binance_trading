"""Migration script to update order_id column size in executions table."""

import os
from sqlalchemy import create_engine, text
from config import DATABASE_URL

def migrate_order_id_column():
    """Update order_id column size from 100 to 500 characters."""

    # Convert postgresql:// to postgresql+pg8000:// for pg8000 driver
    database_url = DATABASE_URL
    if database_url and database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+pg8000://', 1)

    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            print("🔄 Updating executions.order_id column size to 500 characters...")

            # Use ALTER TABLE to modify column size
            conn.execute(text("""
                ALTER TABLE executions
                ALTER COLUMN order_id TYPE VARCHAR(500);
            """))

            conn.commit()
            print("✅ Migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("Note: This is normal if the column is already the correct size.")

if __name__ == "__main__":
    migrate_order_id_column()