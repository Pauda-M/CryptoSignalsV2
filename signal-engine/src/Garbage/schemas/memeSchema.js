export const MEME_TABLE_SCHEMA = `
CREATE TABLE IF NOT EXISTS meme_signals (
    id SERIAL PRIMARY KEY,

    symbol TEXT NOT NULL,

    trend_score DOUBLE PRECISION,
    social_score DOUBLE PRECISION,
    momentum DOUBLE PRECISION,
    alpha DOUBLE PRECISION,

    direction TEXT,
    confidence DOUBLE PRECISION,

    marketcap DOUBLE PRECISION,
    liquidityusd DOUBLE PRECISION,
    volumeusd DOUBLE PRECISION,
    holders INTEGER,
    tradecount INTEGER,
    age_seconds DOUBLE PRECISION,

    buys_5m INTEGER,
    sells_5m INTEGER,
    buys_vs_sells_ratio DOUBLE PRECISION,

    pumpfun_score DOUBLE PRECISION,
    dex_score DOUBLE PRECISION,
    bitquery_score DOUBLE PRECISION,

    created_at TIMESTAMP DEFAULT NOW()
);

-- proper indexes
CREATE INDEX IF NOT EXISTS idx_meme_signals_symbol ON meme_signals(symbol);
CREATE INDEX IF NOT EXISTS idx_meme_signals_created_at ON meme_signals(created_at);
CREATE INDEX IF NOT EXISTS idx_meme_signals_direction ON meme_signals(direction);
CREATE INDEX IF NOT EXISTS idx_meme_signals_confidence ON meme_signals(confidence);
`;
