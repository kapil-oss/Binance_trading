#!/usr/bin/env python3
"""
Apply authentication migration to add login system to the database.
Run this script to add user authentication tables and default admin user.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from config import DATABASE_URL
    from sqlalchemy import create_engine, text
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you have installed the required dependencies:")
    print("pip install psycopg2-binary sqlalchemy")
    sys.exit(1)


def apply_migration():
    """Apply the authentication migration"""

    # Read the SQL migration file
    migration_file = project_root / "auth_migration.sql"
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False

    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
    except Exception as e:
        print(f"❌ Error reading migration file: {e}")
        return False

    # Connect to database
    try:
        # Use psycopg2 directly for better SQL execution
        if DATABASE_URL.startswith('postgresql://'):
            db_url = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)
        else:
            db_url = DATABASE_URL

        # Extract connection parameters
        from urllib.parse import urlparse
        parsed = urlparse(db_url)

        connection = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/'),
            user=parsed.username,
            password=parsed.password
        )
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()

        print("🔗 Connected to database")

        # Execute the migration
        print("🚀 Applying authentication migration...")
        cursor.execute(migration_sql)

        print("✅ Authentication migration applied successfully!")
        print("\n📋 Summary of changes:")
        print("  • Created users table with authentication fields")
        print("  • Created user_sessions table for session management")
        print("  • Created user_roles and user_role_assignments tables")
        print("  • Created login_attempts table for security monitoring")
        print("  • Created password_history table")
        print("  • Created api_keys table for API access")
        print("  • Added user_id column to strategy_preferences table")
        print("  • Created default admin user and roles")
        print("\n🔐 Default Login Credentials:")
        print("  Username: admin")
        print("  Email: admin@alsatrade.com")
        print("  Password: password")
        print("  ⚠️  CHANGE THE DEFAULT PASSWORD IMMEDIATELY!")

        cursor.close()
        connection.close()
        return True

    except Exception as e:
        print(f"❌ Database error: {e}")
        print(f"🔍 Database URL: {DATABASE_URL}")
        return False


def verify_migration():
    """Verify that the migration was applied correctly"""
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # Check if users table exists
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'users'
            """))

            if result.fetchone():
                print("✅ Verification passed: users table exists")

                # Check if admin user exists
                result = conn.execute(text("""
                    SELECT username, email, is_admin FROM users WHERE username = 'admin'
                """))
                admin_user = result.fetchone()

                if admin_user:
                    print(f"✅ Default admin user created: {admin_user[0]} ({admin_user[1]})")
                    return True
                else:
                    print("⚠️  Admin user not found")
                    return False
            else:
                print("❌ Verification failed: users table not found")
                return False

    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False


if __name__ == "__main__":
    print("🔧 AlsaTrade Authentication Migration")
    print("=====================================")

    if not DATABASE_URL:
        print("❌ DATABASE_URL not configured")
        sys.exit(1)

    print(f"🎯 Target database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'localhost'}")

    # Apply migration
    if apply_migration():
        print("\n🔍 Verifying migration...")
        if verify_migration():
            print("\n🎉 Authentication system successfully installed!")
            print("\nNext steps:")
            print("1. Change the default admin password")
            print("2. Create additional user accounts")
            print("3. Update your API to use the new authentication system")
        else:
            print("\n⚠️  Migration applied but verification failed")
            sys.exit(1)
    else:
        print("\n❌ Migration failed")
        sys.exit(1)