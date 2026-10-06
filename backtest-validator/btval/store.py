"""btval's OWN database. Never the trading database.

Default is SQLite at ./btval.db; set BTVAL_DB_URL to a dedicated Postgres
(e.g. the btval-db container in docker-compose.yml). The URL must not point at
a pbTradeNet / pbMasterData instance -- `assert_not_trading_db` refuses the
known ones so a copy-pasted DSN fails loudly instead of creating tables in prod.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import (JSON, BigInteger, Boolean, Column, DateTime, Float, Integer, MetaData,
                        String, Table, Text, UniqueConstraint, create_engine, insert, select)
from sqlalchemy.engine import Engine, make_url

DEFAULT_URL = "sqlite:///./btval.db"

# host:port pairs of trading/market databases btval must never own tables in.
FORBIDDEN_TARGETS = {("192.168.50.88", 15432), ("192.168.50.88", 15442),
                     ("192.168.50.88", 25432), ("192.168.50.88", 5432)}
FORBIDDEN_DBNAMES = {"pbtradenet", "pbmasterdata", "pbquant", "pb_mldata", "pbcicdstage"}

md = MetaData()

fills = Table(
    "fills", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("venue", String(32), nullable=False),        # 'binance' | 'pbfinance' | ...
    Column("source_db", String(128), nullable=False),   # free-text label of where rows came from
    Column("source_row_id", BigInteger, nullable=False),
    Column("session_id", BigInteger), Column("position_id", BigInteger),
    Column("position_group_id", String(128)),
    Column("strategy_id", BigInteger), Column("strategy_name", String(256)),
    Column("symbol", String(32), nullable=False), Column("direction", String(8), nullable=False),
    Column("signal_price", Float), Column("entry_price", Float, nullable=False),
    Column("exit_price", Float), Column("size_usd", Float), Column("notional_usd", Float),
    Column("leverage", Float), Column("pnl_usd", Float), Column("fee_usd", Float),
    Column("funding_usd", Float), Column("exit_reason", String(64)), Column("exit_is_maker", Boolean),
    Column("signal_score", Float),
    Column("signal_bucket_ts", DateTime(timezone=True)),
    Column("opened_at", DateTime(timezone=True)), Column("closed_at", DateTime(timezone=True)),
    Column("ingested_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("venue", "source_db", "source_row_id", name="uq_fill_source"),
)

runs = Table(
    "validation_runs", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("kind", String(16), nullable=False),          # strategy | signal
    Column("subject", String(256)),
    Column("verdict", String(16), nullable=False),
    Column("prior_trials", Integer),
    Column("kill_conditions", JSON),
    Column("report", JSON, nullable=False),
)

calibrations = Table(
    "calibrations", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("filters", JSON, nullable=False),
    Column("result", JSON, nullable=False),
)

paper_sessions = Table(
    "paper_sessions", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("status", String(16), nullable=False),        # active | halted | stopped
    Column("strategy", String(256), nullable=False),
    Column("params", JSON, nullable=False),
    Column("symbol", String(32), nullable=False),
    Column("interval", String(8), nullable=False),
    Column("venue_host", String(256), nullable=False),
    Column("initial_capital", Float, nullable=False),
    Column("max_leverage", Float, nullable=False),
    Column("max_order_notional", Float, nullable=False),
    Column("cost_model", JSON, nullable=False),
    Column("kill_conditions", JSON),
    Column("validation_run_id", Integer),
    Column("unvalidated", Boolean, nullable=False, default=False),
    Column("halted_reason", Text),
)

paper_orders = Table(
    "paper_orders", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("session_id", Integer, nullable=False),
    Column("bar_ts", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("status", String(16), nullable=False),       # pending | filled | no_trade | error
    Column("kind", String(16), nullable=False),         # signal | halt
    Column("symbol", String(32), nullable=False),
    Column("signal", Float), Column("target_qty", Float), Column("prev_qty", Float),
    Column("order_qty", Float), Column("decision_price", Float),
    Column("client_order_id", String(64), nullable=False),
    Column("venue_order_id", String(64)), Column("venue_status", String(32)),
    Column("venue_avg_price", Float), Column("venue_executed_qty", Float),
    Column("venue_drift_bps", Float),                   # venue fill vs decision price, adverse +
    Column("slippage_bps_applied", Float), Column("realistic_price", Float),
    Column("fee_usd", Float), Column("note", Text), Column("venue_raw", JSON),
    UniqueConstraint("session_id", "bar_ts", "kind", name="uq_one_decision_per_bar"),
)

paper_equity = Table(
    "paper_equity", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("session_id", Integer, nullable=False),
    Column("bar_ts", DateTime(timezone=True), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    Column("price", Float, nullable=False),
    Column("position_qty", Float, nullable=False),
    Column("equity", Float, nullable=False),
    Column("drawdown_pct", Float, nullable=False),
    Column("signal", Float),
    Column("action", String(16)),
    Column("alerts", JSON),
    Column("reconcile_diverged", Boolean),
    UniqueConstraint("session_id", "bar_ts", name="uq_equity_bar"),
)

FILL_COLUMNS = [c.name for c in fills.columns if c.name not in ("id", "ingested_at")]


def assert_not_trading_db(url: str) -> None:
    u = make_url(url)
    if u.get_backend_name() == "sqlite":
        return
    if (u.host, u.port or 5432) in FORBIDDEN_TARGETS or (u.database or "").lower() in FORBIDDEN_DBNAMES:
        raise RuntimeError(f"BTVAL_DB_URL points at a trading database ({u.host}:{u.port}/{u.database}). "
                           "btval keeps its own store; use sqlite or the btval-db instance.")


class Store:
    def __init__(self, url: str | None = None):
        self.url = url or os.environ.get("BTVAL_DB_URL", DEFAULT_URL)
        assert_not_trading_db(self.url)
        self.engine: Engine = create_engine(self.url, future=True, pool_pre_ping=True)
        md.create_all(self.engine)

    # -- fills ------------------------------------------------------------
    def upsert_fills(self, rows: list[dict], venue: str, source_db: str) -> dict:
        now = datetime.now(timezone.utc)
        clean = []
        for r in rows:
            d = {k: r.get(k) for k in FILL_COLUMNS if k in r}
            d["venue"], d["source_db"], d["ingested_at"] = venue, source_db, now
            d["source_row_id"] = int(r.get("source_row_id", r.get("id")))
            for ts in ("signal_bucket_ts", "opened_at", "closed_at"):
                if isinstance(d.get(ts), str):
                    d[ts] = pd.Timestamp(d[ts]).to_pydatetime()
            clean.append(d)
        if not clean:
            return {"received": 0, "inserted": 0}
        with self.engine.begin() as cx:
            existing = set(cx.execute(
                select(fills.c.source_row_id).where(fills.c.venue == venue, fills.c.source_db == source_db,
                                                    fills.c.source_row_id.in_([c["source_row_id"] for c in clean]))
            ).scalars())
            new = [c for c in clean if c["source_row_id"] not in existing]
            if new:
                cx.execute(insert(fills), new)
        return {"received": len(clean), "inserted": len(new), "duplicates": len(clean) - len(new)}

    def max_source_row_id(self, venue: str, source_db: str) -> int:
        with self.engine.connect() as cx:
            v = cx.execute(select(fills.c.source_row_id).where(fills.c.venue == venue, fills.c.source_db == source_db)
                           .order_by(fills.c.source_row_id.desc()).limit(1)).scalar()
        return int(v or 0)

    def load_fills(self, venue: str | None = None, strategy_id: int | None = None,
                   symbol: str | None = None, since: str | None = None, until: str | None = None) -> pd.DataFrame:
        q = select(fills)
        if venue:
            q = q.where(fills.c.venue == venue)
        if strategy_id is not None:
            q = q.where(fills.c.strategy_id == strategy_id)
        if symbol:
            q = q.where(fills.c.symbol == symbol)
        if since:
            q = q.where(fills.c.opened_at >= pd.Timestamp(since, tz="UTC").to_pydatetime())
        if until:
            q = q.where(fills.c.opened_at < pd.Timestamp(until, tz="UTC").to_pydatetime())
        with self.engine.connect() as cx:
            df = pd.read_sql(q, cx)
        for ts in ("signal_bucket_ts", "opened_at", "closed_at"):
            if ts in df:
                df[ts] = pd.to_datetime(df[ts], utc=True)
        return df

    # -- runs -------------------------------------------------------------
    def save_run(self, kind: str, subject: str, report: dict, prior_trials: int | None = None) -> int:
        with self.engine.begin() as cx:
            res = cx.execute(insert(runs).values(
                created_at=datetime.now(timezone.utc), kind=kind, subject=subject,
                verdict=report["verdict"], prior_trials=prior_trials,
                kill_conditions=report.get("kill_conditions"),
                report=json.loads(json.dumps(report, default=str))))
            return int(res.inserted_primary_key[0])

    def list_runs(self, limit: int = 50) -> list[dict]:
        q = select(runs.c.id, runs.c.created_at, runs.c.kind, runs.c.subject, runs.c.verdict,
                   runs.c.prior_trials).order_by(runs.c.id.desc()).limit(limit)
        with self.engine.connect() as cx:
            return [dict(r._mapping) for r in cx.execute(q)]

    def get_run(self, run_id: int) -> dict | None:
        with self.engine.connect() as cx:
            r = cx.execute(select(runs).where(runs.c.id == run_id)).first()
        return dict(r._mapping) if r else None

    def list_calibrations(self, limit: int = 20) -> list[dict]:
        q = select(calibrations).order_by(calibrations.c.id.desc()).limit(limit)
        with self.engine.connect() as cx:
            out = []
            for r in cx.execute(q):
                d = dict(r._mapping)
                res = d.pop("result") or {}
                d["recommended_config"] = res.get("recommended_config")
                d["n_positions"] = res.get("n_positions")
                d["entry_slippage_bps"] = {k: v for k, v in (res.get("entry_slippage_bps") or {}).items()
                                           if k in ("mean", "p90", "n")}
                out.append(d)
            return out

    def get_calibration(self, cal_id: int) -> dict | None:
        with self.engine.connect() as cx:
            r = cx.execute(select(calibrations).where(calibrations.c.id == cal_id)).first()
        return dict(r._mapping) if r else None

    def save_calibration(self, filters: dict, result: dict) -> int:
        with self.engine.begin() as cx:
            res = cx.execute(insert(calibrations).values(
                created_at=datetime.now(timezone.utc), filters=filters,
                result=json.loads(json.dumps(result, default=str))))
            return int(res.inserted_primary_key[0])
