import os
import numpy as np
import pandas as pd
import psycopg2
import xgboost as xgb
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env var not set")

def load_spread_from_pg(limit=None):
    conn = psycopg2.connect(DATABASE_URL)
    q = "SELECT ts, spread_log, xrp_volume, btc_volume FROM xrp_btc_hourly_spread ORDER BY ts"
    if limit:
        q += " LIMIT %s"
        df = pd.read_sql(q, conn, params=(limit,))
    else:
        df = pd.read_sql(q, conn)
    conn.close()
    return df

def build_flat_dataset(df, window=168):
    spread = df["spread_log"].values.astype("float64")
    xvol = df["xrp_volume"].values.astype("float64")
    bvol = df["btc_volume"].values.astype("float64")

    xvol_z = (xvol - xvol.mean()) / (xvol.std() + 1e-8)
    bvol_z = (bvol - bvol.mean()) / (bvol.std() + 1e-8)

    X_list = []
    y1_list, y4_list, y24_list = [], [], []
    H1, H4, H24 = 1, 4, 24
    max_h = H24

    for i in range(window - 1, len(spread) - max_h):
        s_win = spread[i - window + 1 : i + 1]
        xv_win = xvol_z[i - window + 1 : i + 1]
        bv_win = bvol_z[i - window + 1 : i + 1]

        feat = np.concatenate([s_win, xv_win, bv_win], axis=0)

        s_now = spread[i]
        y1 = spread[i + H1] - s_now
        y4 = spread[i + H4] - s_now
        y24 = spread[i + H24] - s_now

        X_list.append(feat)
        y1_list.append(y1)
        y4_list.append(y4)
        y24_list.append(y24)

    X = np.stack(X_list, axis=0)
    y1 = np.array(y1_list, dtype="float64")
    y4 = np.array(y4_list, dtype="float64")
    y24 = np.array(y24_list, dtype="float64")
    return X, y1, y4, y24

if __name__ == "__main__":
    print("Loading spread data from PostgreSQL...")
    df = load_spread_from_pg()
    print(f"Loaded {len(df)} rows.")
    X, y1, y4, y24 = build_flat_dataset(df)
    print("Flat dataset shape:", X.shape)

    for lbl, y in [("1h", y1), ("4h", y4), ("24h", y24)]:
        dtrain = xgb.DMatrix(X, label=y)
        params = {"objective": "reg:squarederror", "eta": 0.05, "max_depth": 6}
        model = xgb.train(params, dtrain, num_boost_round=300)
        model.save_model(f"xgb_pg_model_{lbl}.json")
        print(f"Saved xgb_pg_model_{lbl}.json")
