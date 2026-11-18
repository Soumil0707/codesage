"""Helper script to initialize the MySQL database and create all tables."""
import sys
import pymysql
from app.config import get_settings
from app.database import Base, sync_engine

settings = get_settings()

def init():
    print(f"Connecting to MySQL for CodeSage initialization...")
    # 1. Connect without db name first to ensure database exists
    sync_url = settings.DATABASE_URL_SYNC
    # Parse connection info from sync_url: mysql+pymysql://user:pass@host:port/dbname
    from urllib.parse import urlparse
    parsed = urlparse(sync_url.replace("mysql+pymysql://", "http://"))
    user = parsed.username or "root"
    password = parsed.password or ""
    host = parsed.hostname or "localhost"
    port = parsed.port or 3306
    db_name = parsed.path.lstrip("/") or "codesage"

    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=port,
            connect_timeout=5,
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            print(f"Database `{db_name}` verified/created.")
        conn.close()
    except Exception as e:
        print(f"\n[ERROR] Failed to connect to MySQL server at {host}:{port}")
        print(f"Details: {e}")
        print("\nPlease make sure MySQL is running:")
        print("  - If using XAMPP: Open XAMPP Control Panel and click 'Start' next to MySQL.")
        print("  - Or start via: C:\\xampp\\mysql_start.bat")
        sys.exit(1)

    # 2. Create tables via SQLAlchemy metadata
    try:
        Base.metadata.create_all(bind=sync_engine)
        print("All 15 CodeSage database tables created successfully!")
        print("\nYou can now start the backend with:")
        print("  python -m uvicorn app.main:app --reload --port 8000")
    except Exception as e:
        print(f"[ERROR] Failed to create tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init()
