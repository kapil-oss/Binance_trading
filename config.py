import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Binance Configuration
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
BINANCE_USE_TESTNET = os.getenv("BINANCE_USE_TESTNET", "1").lower() in ("1", "true", "yes", "on")

# Application Configuration
APP_TITLE = "Alsa Trade App"
APP_HOST = "0.0.0.0"
APP_PORT = int(os.getenv("PORT", "8000"))