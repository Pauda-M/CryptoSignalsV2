
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(DATABASE_URL)

def main():
    conn = get_conn()
    cur = conn.cursor()
    print("=== Distinct symbols in market_candles (by interval) ===")
    cur.execute(
        """
        SELECT symbol, interval, COUNT(*) AS cnt
        FROM market_candles
        GROUP BY symbol, interval
        ORDER BY symbol, interval;
        """
    )
    rows = cur.fetchall()
    for sym, interval, cnt in rows:
        print(f"symbol={sym}, interval={interval}, rows={cnt}")

    print("\n=== Sanity check: expecting only BTCUSDT and XRPUSDT for 1h data ===")
    bad = [r for r in rows if r[1] == "1h" and r[0] not in ("BTCUSDT", "XRPUSDT")]
    if bad:
        print("WARNING: Found unexpected symbols for 1h interval:")
        for sym, interval, cnt in bad:
            print(f"  -> {sym} ({interval}) rows={cnt}")
    else:
        print("OK: Only BTCUSDT and XRPUSDT found for 1h (or no 1h data).")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
