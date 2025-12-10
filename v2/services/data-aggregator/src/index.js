/*
 * Data Aggregator Service
 * Placeholder: aggregates market data from multiple sources
 */

require('dotenv').config({ path: '../../.env' });

const port = process.env.DATA_AGGREGATOR_PORT || 5001;

console.log(`[Data Aggregator] Starting on port ${port}...`);
console.log('[Data Aggregator] Aggregating data from multiple sources');

// TODO: Implement actual data aggregation logic
// - Fetch OHLC from Binance
// - Fetch DEX data from Dexscreener
// - Store in PostgreSQL
// - Emit via WebSocket

console.log('[Data Aggregator] Listening for data aggregation requests');
