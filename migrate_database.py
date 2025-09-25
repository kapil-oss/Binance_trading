#!/usr/bin/env python3
"""Database migration script to add timing columns to executions table."""

from sqlalchemy import text
from database import engine

def migrate_database():
    """Add missing timing columns to executions table."""
    with engine.connect() as connection:
        try:
            # Check if columns already exist
            result = connection.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'executions' AND column_name = 'signal_sent_time'
            """))

            if result.fetchone() is None:
                print("Adding timing columns to executions table...")

                # Add the timing columns
                connection.execute(text("""
                    ALTER TABLE executions
                    ADD COLUMN signal_sent_time TIMESTAMP,
                    ADD COLUMN received_time TIMESTAMP,
                    ADD COLUMN processed_time TIMESTAMP,
                    ADD COLUMN sent_to_binance_time TIMESTAMP,
                    ADD COLUMN binance_executed_time TIMESTAMP
                """))

                connection.commit()
                print("Successfully added timing columns to executions table.")
            else:
                print("Timing columns already exist in executions table.")

        except Exception as e:
            print(f"Error during migration: {e}")
            connection.rollback()
            raise

if __name__ == "__main__":
    migrate_database()