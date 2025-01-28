# bot.py

import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from typing import Dict, Optional, List
import threading

# Import configuration
from config import DB_CONFIG, FILTERS, BLACKLISTS, RUGCHECK_API, TELEGRAM_CONFIG

# Add this to the above at some point BUNDLED_SUPPLY_SETTINGS,

# DexScreener API endpoint
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"

class DexScreenerBot:
    def __init__(self):
        self.engine = create_engine(
            f'postgresql+psycopg2://{DB_CONFIG["user"]}:{DB_CONFIG["password"]}'
            f'@{DB_CONFIG["host"]}/{DB_CONFIG["dbname"]}'
        )
        self._init_db()

    def _init_db(self):
        """Initialize the database schema if it doesn't exist."""
        with self.engine.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    id SERIAL PRIMARY KEY,
                    pair_address VARCHAR(64) UNIQUE,
                    base_token_name VARCHAR(64),
                    base_token_address VARCHAR(64),
                    quote_token_address VARCHAR(64),
                    price NUMERIC,
                    liquidity NUMERIC,
                    volume_24h NUMERIC,
                    chain VARCHAR(32),
                    exchange VARCHAR(32),
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(32) CHECK (status IN ('rugged', 'pumped', 'cex_listed'))
                );

                CREATE TABLE IF NOT EXISTS blacklist (
                    address VARCHAR(64) PRIMARY KEY,
                    type VARCHAR(20) CHECK (type IN ('coin', 'dev')),
                    reason TEXT,
                    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_blacklist_type ON blacklist(type);
            """)
            # Seed initial blacklists
            self._seed_initial_blacklists()

    def _seed_initial_blacklists(self):
        """Seed the database with initial blacklists from the config."""
        with self.engine.connect() as conn:
            # Seed coin blacklist
            for address in BLACKLISTS["coin_blacklist"]:
                conn.execute("""
                    INSERT INTO blacklist (address, type, reason)
                    VALUES (%s, 'coin', 'Initial seed')
                    ON CONFLICT (address) DO NOTHING;
                """, (address,))

            # Seed dev blacklist
            for address in BLACKLISTS["dev_blacklist"]:
                conn.execute("""
                    INSERT INTO blacklist (address, type, reason)
                    VALUES (%s, 'dev', 'Initial seed')
                    ON CONFLICT (address) DO NOTHING;
                """, (address,))

    def fetch_token_data(self, token_address: str) -> Optional[Dict]:
        """Fetch token data from DexScreener."""
        try:
            response = requests.get(f"{DEXSCREENER_API}{token_address}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching data for token {token_address}: {e}")
            return None

    def check_rugcheck_score(self, token_address: str) -> bool:
        """Check if the token is marked as 'Good' on RugCheck.xyz."""
        try:
            response = requests.get(
                f"{RUGCHECK_API['endpoint']}/{token_address}"
            )
            response.raise_for_status()
            data = response.json()
            return data.get("score", 0) >= RUGCHECK_API["min_score"]
        except requests.RequestException as e:
            print(f"Error checking RugCheck score for token {token_address}: {e}")
            return False

    def check_bundled_supply(self, token_address: str) -> bool:
        """Check if the token supply is bundled."""
        try:
            # Fetch holder distribution data (example API)
            response = requests.get(
                f"https://api.example.com/holders/{token_address}"
            )
            response.raise_for_status()
            holders = response.json().get("holders", [])

            # Check if top holders control too much supply
            top_holders = sorted(holders, key=lambda x: x['percentage'], reverse=True)[:BUNDLED_SUPPLY_SETTINGS["max_top_holders"]]
            total_percentage = sum(h['percentage'] for h in top_holders)

            if total_percentage > BUNDLED_SUPPLY_SETTINGS["max_top_holder_percentage"]:
                return True
            return False
        except requests.RequestException as e:
            print(f"Error checking bundled supply for token {token_address}: {e}")
            return False

    def apply_filters(self, token_data: Dict) -> bool:
        """Apply filters to determine if the token should be processed."""
        # Chain whitelist filter
        if token_data['chainId'] not in FILTERS["chain_whitelist"]:
            return False

        # Liquidity filter
        if float(token_data['liquidity']['usd']) < FILTERS["min_liquidity"]:
            return False

        # Age filter
        min_age = datetime.now() - timedelta(days=FILTERS["min_age_days"])
        created_at = datetime.fromtimestamp(token_data['pairCreatedAt'] / 1000)
        if created_at > min_age:
            return False

        # Blacklist filters
        with self.engine.connect() as conn:
            # Check coin blacklist
            coin_blacklisted = conn.execute("""
                SELECT 1 FROM blacklist
                WHERE type = 'coin'
                AND (address = %s OR address = %s);
            """, (token_data['baseToken']['address'], token_data['baseToken']['name'])).scalar()

            # Check dev blacklist
            dev_blacklisted = conn.execute("""
                SELECT 1 FROM blacklist
                WHERE type = 'dev'
                AND address = %s;
            """, (token_data['baseToken']['address'],)).scalar()

            if coin_blacklisted or dev_blacklisted:
                return False

        # RugCheck.xyz verification
        if not self.check_rugcheck_score(token_data['baseToken']['address']):
            print(f"Token {token_data['baseToken']['name']} failed RugCheck verification.")
            return False

        # Bundled supply check
        if self.check_bundled_supply(token_data['baseToken']['address']):
            print(f"Token {token_data['baseToken']['name']} has bundled supply. Blacklisting token and developer.")
            self.add_to_blacklist(token_data['baseToken']['address'], "coin", "Bundled supply")
            self.add_to_blacklist(token_data['baseToken']['address'], "dev", "Bundled supply")
            return False

        return True

    def add_to_blacklist(self, address: str, list_type: str, reason: str):
        """Add an address to the blacklist."""
        with self.engine.connect() as conn:
            conn.execute("""
                INSERT INTO blacklist (address, type, reason)
                VALUES (%s, %s, %s)
                ON CONFLICT (address) DO UPDATE SET reason = EXCLUDED.reason;
            """, (address, list_type, reason))

    def send_telegram_message(self, message: str):
        """Send a message via Telegram."""
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_CONFIG['bot_token']}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CONFIG["chat_id"],
                    "text": message
                }
            )
        except requests.RequestException as e:
            print(f"Error sending Telegram message: {e}")

    def execute_trade_via_bonkbot(self, token_address: str, action: str):
        """Execute a trade via BonkBot."""
        try:
            response = requests.post(
                f"{TELEGRAM_CONFIG['bonkbot_api']}/trade",
                json={
                    "token_address": token_address,
                    "action": action  # "buy" or "sell"
                }
            )
            response.raise_for_status()
            self.send_telegram_message(f"{action.capitalize()} order executed for token: {token_address}")
        except requests.RequestException as e:
            print(f"Error executing trade via BonkBot: {e}")

    def save_token_data(self, token_data: Dict, status: str):
        """Save token data to the database."""
        with self.engine.connect() as conn:
            conn.execute("""
                INSERT INTO tokens (
                    pair_address, base_token_name, base_token_address,
                    quote_token_address, price, liquidity, volume_24h,
                    chain, exchange, created_at, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (pair_address) DO UPDATE SET
                    price = EXCLUDED.price,
                    liquidity = EXCLUDED.liquidity,
                    volume_24h = EXCLUDED.volume_24h,
                    updated_at = CURRENT_TIMESTAMP,
                    status = EXCLUDED.status;
            """, (
                token_data['pairAddress'],
                token_data['baseToken']['name'],
                token_data['baseToken']['address'],
                token_data['quoteToken']['address'],
                float(token_data['priceUsd']),
                float(token_data['liquidity']['usd']),
                float(token_data['volume']['h24']),
                token_data['chainId'],
                token_data['dexId'],
                datetime.fromtimestamp(token_data['pairCreatedAt'] / 1000),
                status
            ))

    def run(self):
        """Main loop to fetch, save, and analyze token data."""
        token_addresses = [
            "0x...",  # Add token addresses to monitor
        ]

        for address in token_addresses:
            token_data = self.fetch_token_data(address)
            if token_data and self.apply_filters(token_data):
                status = self.determine_status(token_data)
                self.save_token_data(token_data, status)

                # Execute trade via BonkBot
                if status == "pumped":
                    self.execute_trade_via_bonkbot(token_data['baseToken']['address'], "buy")
                elif status == "rugged":
                    self.execute_trade_via_bonkbot(token_data['baseToken']['address'], "sell")

# Run the bot in a separate thread
def run_bot():
    bot = DexScreenerBot()
    bot.run()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # Run the Streamlit app
    import subprocess
    subprocess.run(["streamlit", "run", "app.py"])