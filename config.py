# config.py

# Database configuration
DB_CONFIG = {
    "dbname": "dexscreener",
    "user": "admin",
    "password": "your_password",
    "host": "localhost",
    "port": "5432"
}

# Filters
FILTERS = {
    "min_liquidity": 5000,  # Minimum liquidity in USD
    "min_age_days": 3,      # Minimum age of the token in days
    "max_price_change_24h": 50,  # Maximum allowed price change in 24 hours (%)
    "chain_whitelist": ["solana", "ethereum", "binance-smart-chain"]  # Allowed chains
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
    ]
}

# RugCheck.xyz API
RUGCHECK_API = {
    "endpoint": "https://rugcheck.xyz/api/token",
    "min_score": 80  # Minimum score to consider a token "Good"
}

# Bundled Supply Settings
BUNDLED_SUPPLY_SETTINGS = {
    "max_top_holder_percentage": 20,  # Max percentage of supply held by a single wallet
    "max_top_holders": 3              # Max number of wallets holding significant supply
}

# Telegram Configuration
TELEGRAM_CONFIG = {
    "bot_token": "your_telegram_bot_token",  # Your Telegram bot token
    "chat_id": "your_chat_id",               # Your Telegram chat ID
    "bonkbot_api": "https://bonkbot.io/api"  # BonkBot API endpoint
}