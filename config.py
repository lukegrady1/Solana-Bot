from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Database configuration
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

# Filters
FILTERS = {
    "min_liquidity": 5000,  # Minimum liquidity in USD
    "min_age_days": 3,      # Minimum age of the token in days
    "max_price_change_24h": 50,  # Maximum allowed price change in 24 hours (%)
    "chain_whitelist": ["solana", "ethereum", "binance-smart-chain"],  # Allowed chains
}

# Blacklists
BLACKLISTS = {
    "coin_blacklist": [
        "0x123...def",  # Known scam token address
        "SUSPECTCOIN"   # Blacklisted symbol
    ],
    "dev_blacklist": [
        "0x456...abc",  # Known rug developer address
        "0x789...fed"   # Another scam developer
    ],
}

# RugCheck.xyz API
RUGCHECK_API = {
    "endpoint": os.getenv("RUGCHECK_API_ENDPOINT"),
    "min_score": int(os.getenv("RUGCHECK_MIN_SCORE", 80)),  # Default to 80 if not set
}

# Telegram Configuration
TELEGRAM_CONFIG = {
    "bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
    "chat_id": os.getenv("TELEGRAM_CHAT_ID"),
    "bonkbot_api": os.getenv("BONKBOT_API"),
}
