// alerts.js
// Generates alerts from v_pumpx_live rows (corrected to match real columns)

export default function generatePumpAlerts(rows) {
  const alerts = [];

  for (const t of rows) {
    const buys5m = Number(t.buys_5m ?? 0);
    const vol5m = Number(t.volume_5m ?? 0);
    const mcap = Number(t.marketcap ?? 0);
    const pumpProb = Number(t.pump_probability ?? 0);
    const priceChange1h = Number(t.price_change_1h ?? 0);

    // ---- ALERT RULES ----
    // You can adjust threshold
    const meetsRule =
      (
        buys5m >= 20 ||
        priceChange1h >= 5 ||     // <--- using your 1h price change
        pumpProb >= 0.6
      ) &&
      mcap >= 3000 &&
      vol5m >= 50;

    if (!meetsRule) continue;

    alerts.push({
      id: t.mint, // stable id for Option-D
      mint: t.mint,
      token_id: t.token_id,
      symbol: t.symbol,
      name: t.name,
      price: Number(t.price),
      marketcap: mcap,
      buys5m,
      vol5m,
      priceChange1h,
      pumpProb,
      updated_at: t.updated_at,
      timestamp: new Date().toISOString()
    });
  }

  return alerts;
}
