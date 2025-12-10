export function computeTrend(t) {
  const pump = Number(t.pump_probability || 0);
  const pumpPct = pump * 100;

  const priceChange1h = Number(t.price_change_1h || 0) * 100;
  const bp = (Number(t.buys_5m) || 0) - (Number(t.sells_5m) || 0);
  const vol = Number(t.volume_5m || 0);

  return (
    pumpPct +
    priceChange1h * 0.5 +
    bp * 0.5 +
    vol / 1000
  );
}
