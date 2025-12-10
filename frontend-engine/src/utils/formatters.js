export function fmt(x, decimals = 3) {
  const n = Number(x);
  if (!Number.isFinite(n)) return "-";
  return n.toFixed(decimals);
}

export function pct(x, decimals = 1) {
  const n = Number(x);
  if (!Number.isFinite(n)) return "-";
  return (n * 100).toFixed(decimals) + "%";
}
