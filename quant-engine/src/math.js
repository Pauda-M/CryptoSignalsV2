export function mean(arr) {
  if (!arr.length) return NaN;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

export function stdDev(arr) {
  if (arr.length < 2) return NaN;
  const m = mean(arr);
  const varSum = arr.reduce((acc, v) => acc + (v - m) * (v - m), 0);
  return Math.sqrt(varSum / (arr.length - 1));
}

export function downsideStdDev(arr) {
  const negatives = arr.filter((r) => r < 0);
  if (negatives.length < 2) return NaN;
  return stdDev(negatives);
}

export function percentile(arr, p) {
  if (!arr.length) return NaN;
  const sorted = [...arr].sort((a, b) => a - b);
  const idx = Math.max(0, Math.min(sorted.length - 1, Math.floor(p * (sorted.length - 1))));
  return sorted[idx];
}

export function maxDrawdown(values) {
  if (!values.length) return 0;
  let peak = values[0];
  let maxDd = 0;
  for (const v of values) {
    if (v > peak) peak = v;
    const dd = (v - peak) / peak;
    if (dd < maxDd) maxDd = dd;
  }
  return maxDd; // negative number
}
