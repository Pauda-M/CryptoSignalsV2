import dotenv from "dotenv";
dotenv.config();

import { pool } from "./db.js";
import { fetchAndStoreDailyOhlc, loadDailyOhlcFromDb } from "./ohlcFetcher.js";
import { mean, stdDev, downsideStdDev, percentile, maxDrawdown } from "./math.js";

const LOOKBACK_DAYS = Number(process.env.QUANT_LOOKBACK_DAYS || 90);
const LOOP_MS = Number(process.env.QUANT_LOOP_INTERVAL_MS || 15 * 60_000);

async function getPortfolios() {
  const res = await pool.query(
    `
    SELECT id, name, base_currency
    FROM portfolios
    ORDER BY created_at ASC;
    `
  );
  return res.rows;
}

async function getPositions(portfolioId) {
  const res = await pool.query(
    `
    SELECT symbol, quantity
    FROM portfolio_positions
    WHERE portfolio_id = $1
    ORDER BY symbol;
    `,
    [portfolioId]
  );
  return res.rows;
}

async function computePortfolioMetrics(portfolioId) {
  const positions = await getPositions(portfolioId);
  if (!positions.length) {
    console.log(`[QUANT] Portfolio ${portfolioId} has no positions; skipping.`);
    return;
  }

  // Step 1: ensure OHLC for each symbol and load it
  const priceSeriesBySymbol = {};

  for (const pos of positions) {
    const symbol = pos.symbol;
    console.log(`[QUANT] Ensuring OHLC for ${symbol}`);
    await fetchAndStoreDailyOhlc(symbol);
    const candles = await loadDailyOhlcFromDb(symbol);
    if (candles.length === 0) {
      console.warn(`[QUANT] No OHLC for ${symbol}, will be ignored in metrics.`);
      continue;
    }
    priceSeriesBySymbol[symbol] = candles;
  }

  const symbols = Object.keys(priceSeriesBySymbol);
  if (!symbols.length) {
    console.warn(`[QUANT] No usable symbols for portfolio ${portfolioId}`);
    return;
  }

  // Step 2: build portfolio value time-series
  // Use the first symbol's TS as reference
  const refSymbol = symbols[0];
  const refSeries = priceSeriesBySymbol[refSymbol];

  const values = [];
  const timestamps = [];

  for (let i = 0; i < refSeries.length; i++) {
    const t = refSeries[i].ts;
    let totalValue = 0;

    for (const pos of positions) {
      const symbol = pos.symbol;
      const qty = Number(pos.quantity);
      const series = priceSeriesBySymbol[symbol];
      if (!series || series.length <= i) continue;
      const price = series[i].close;
      totalValue += qty * price;
    }

    if (totalValue > 0) {
      values.push(totalValue);
      timestamps.push(t);
    }
  }

  if (values.length < 3) {
    console.warn(`[QUANT] Not enough data points for portfolio ${portfolioId}`);
    return;
  }

  // Step 3: compute daily returns
  const returns = [];
  for (let i = 1; i < values.length; i++) {
    const r = values[i] / values[i - 1] - 1;
    returns.push(r);
  }

  const periodDays = values.length - 1;
  const totalReturn = values[values.length - 1] / values[0] - 1;

  const dailyMean = mean(returns);
  const dailyVol = stdDev(returns);

  const annualizedReturn =
    periodDays > 0 ? Math.pow(1 + totalReturn, 365 / periodDays) - 1 : NaN;
  const annualizedVol = dailyVol * Math.sqrt(365);

  const sharpe =
    annualizedVol > 0 ? annualizedReturn / annualizedVol : null;

  const dStd = downsideStdDev(returns);
  const annualizedDownsideVol = dStd * Math.sqrt(365);
  const sortino =
    annualizedDownsideVol > 0
      ? annualizedReturn / annualizedDownsideVol
      : null;

  const maxDd = maxDrawdown(values); // negative
  const var95 = percentile(returns, 0.05); // 5% percentile of daily returns

  // concentration index using last day weights
  const lastPrices = {};
  for (const pos of positions) {
    const symbol = pos.symbol;
    const series = priceSeriesBySymbol[symbol];
    if (!series || !series.length) continue;
    lastPrices[symbol] = series[series.length - 1].close;
  }

  const positionValues = [];
  let totalLastValue = 0;
  for (const pos of positions) {
    const symbol = pos.symbol;
    const p = lastPrices[symbol];
    if (!p) continue;
    const v = Number(pos.quantity) * p;
    positionValues.push(v);
    totalLastValue += v;
  }

  let concentrationIndex = null;
  if (totalLastValue > 0) {
    const weights = positionValues.map((v) => v / totalLastValue);
    concentrationIndex = weights.reduce((acc, w) => acc + w * w, 0);
  }

  const metrics = {
    portfolio_id: portfolioId,
    period_days: periodDays,
    total_return: totalReturn,
    annualized_return: annualizedReturn,
    volatility: annualizedVol,
    sharpe_ratio: sharpe,
    sortino_ratio: sortino,
    max_drawdown: maxDd,
    var_95: var95,
    concentration_index: concentrationIndex,
    num_assets: positions.length
  };

  console.log("[QUANT] Metrics", portfolioId, metrics);

  // Step 4: insert snapshot
  await pool.query(
    `
    INSERT INTO portfolio_quant_metrics (
      portfolio_id,
      snapshot_ts,
      period_days,
      total_return,
      annualized_return,
      volatility,
      sharpe_ratio,
      sortino_ratio,
      max_drawdown,
      var_95,
      concentration_index,
      num_assets
    )
    VALUES (
      $1, now(), $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
    );
    `,
    [
      metrics.portfolio_id,
      metrics.period_days,
      metrics.total_return,
      metrics.annualized_return,
      metrics.volatility,
      metrics.sharpe_ratio,
      metrics.sortino_ratio,
      metrics.max_drawdown,
      metrics.var_95,
      metrics.concentration_index,
      metrics.num_assets
    ]
  );
}

async function runOnce() {
  console.log("====================================");
  console.log("  QUANT ENGINE — portfolio metrics");
  console.log("====================================");

  const portfolios = await getPortfolios();
  console.log(`[QUANT] Found ${portfolios.length} portfolios`);

  for (const p of portfolios) {
    try {
      console.log(`[QUANT] Processing portfolio ${p.id} (${p.name})`);
      await computePortfolioMetrics(p.id);
    } catch (err) {
      console.error("[QUANT] Error for portfolio", p.id, err.message);
    }
  }
}

async function mainLoop() {
  const interval = LOOP_MS;
  console.log(
    `[QUANT] Starting loop, every ${(interval / 1000 / 60).toFixed(1)} minutes`
  );

  const loop = async () => {
    try {
      await runOnce();
    } catch (err) {
      console.error("[QUANT] Fatal in loop:", err);
    } finally {
      setTimeout(loop, interval);
    }
  };

  loop();
}

mainLoop().catch((err) => {
  console.error("[QUANT] Fatal startup error:", err);
  process.exit(1);
});
