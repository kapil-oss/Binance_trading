import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.preferences import router as preferences_router
from api.trading import router as trading_router
from config import APP_HOST, APP_PORT, APP_TITLE
from database import init_database

# Initialize FastAPI app
app = FastAPI(title=APP_TITLE)

# Initialize database
init_database()

# Run migration on startup
try:
    from quick_migration import run_migration
    print("🚀 Running database migration on startup...")
    run_migration()
except Exception as e:
    print(f"⚠️ Migration failed on startup: {e}")
    print("🔄 Continuing with app startup...")

# Include routers
app.include_router(trading_router)
app.include_router(preferences_router)

# Serve frontend assets
app.mount("/ui", StaticFiles(directory="frontend", html=True), name="ui")


if __name__ == "__main__":
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
