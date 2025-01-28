# app.py

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from config import DB_CONFIG

# Initialize database connection
engine = create_engine(
    f'postgresql+psycopg2://{DB_CONFIG["user"]}:{DB_CONFIG["password"]}'
    f'@{DB_CONFIG["host"]}/{DB_CONFIG["dbname"]}'
)

# Streamlit app
def main():
    st.title("DexScreener Bot Dashboard")

    # Sidebar for actions
    st.sidebar.header("Actions")
    if st.sidebar.button("Refresh Data"):
        st.experimental_rerun()

    # Display tokens
    st.header("Analyzed Tokens")
    tokens_df = pd.read_sql("SELECT * FROM tokens", engine)
    st.dataframe(tokens_df)

    # Display blacklisted tokens
    st.header("Blacklisted Tokens")
    blacklisted_df = pd.read_sql("SELECT * FROM blacklist WHERE type = 'coin'", engine)
    st.dataframe(blacklisted_df)

    # Display blacklisted developers
    st.header("Blacklisted Developers")
    blacklisted_devs_df = pd.read_sql("SELECT * FROM blacklist WHERE type = 'dev'", engine)
    st.dataframe(blacklisted_devs_df)

    # Visualize token performance
    st.header("Token Performance")
    if not tokens_df.empty:
        st.line_chart(tokens_df.set_index("created_at")["price"])

    # Manual actions
    st.sidebar.header("Manual Actions")
    token_address = st.sidebar.text_input("Enter Token Address to Blacklist")
    reason = st.sidebar.text_input("Reason for Blacklisting")
    if st.sidebar.button("Blacklist Token"):
        if token_address and reason:
            with engine.connect() as conn:
                conn.execute("""
                    INSERT INTO blacklist (address, type, reason)
                    VALUES (%s, 'coin', %s)
                    ON CONFLICT (address) DO UPDATE SET reason = EXCLUDED.reason;
                """, (token_address, reason))
            st.sidebar.success(f"Token {token_address} blacklisted.")
        else:
            st.sidebar.error("Please provide both token address and reason.")

if __name__ == "__main__":
    main()