import pandas as pd
import psycopg2
import os

def load_pg_dataframe(symbol: str, interval: str = "1h"):
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "crypto"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS")
    )
    query = f"""
        SELECT open_time, close, volume, quote_volume, trades_count
        FROM market_candles
        WHERE symbol = '{symbol}'
        AND interval = '{interval}'
        ORDER BY open_time ASC;
    """
    df = pd.read_sql(query, conn)
    conn.close()

    df["open_time"] = pd.to_datetime(df["open_time"])
    return df
