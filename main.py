import uvicorn
from fastapi import FastAPI
from api.trading import router as trading_router
from config import APP_TITLE, APP_HOST, APP_PORT
from database import init_database

# Initialize FastAPI app
app = FastAPI(title=APP_TITLE)

# Initialize database
init_database()

# Include routers
app.include_router(trading_router)

if __name__ == "__main__":
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)