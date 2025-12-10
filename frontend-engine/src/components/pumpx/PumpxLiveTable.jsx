import React from "react";

export default function PumpxLiveTable({ tokens, onSelect }) {
  // Safe debug
  console.log("[TABLE] tokens received:", tokens?.length);

  if (!tokens || tokens.length === 0) {
    return (
      <div style={{ marginTop: 20, color: "#888" }}>
        No tokens matching filters.
      </div>
    );
  }

  return (
    <table className="pumpx-table" style={{ width: "100%", marginTop: 20 }}>
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Mint</th>
          <th>Price</th>
          <th>MC</th>
          <th>Vol 5m</th>
          <th>Buys 5m</th>
          <th>Sells 5m</th>
          <th>Age (s)</th>
          <th>Score</th>
        </tr>
      </thead>
      <tbody>
        {tokens.map((t) => (
          <tr
            key={t.token_id}
            onClick={() => onSelect?.(t)}
            style={{ cursor: "pointer" }}
          >
            <td>{t.symbol || "?"}</td>
            <td style={{ fontSize: 10 }}>{t.mint}</td>
            <td>{Number(t.price).toExponential(3)}</td>
            <td>{Math.round(t.marketcap)}</td>
            <td>{Math.round(t.volume_5m)}</td>
            <td>{t.buys_5m}</td>
            <td>{t.sells_5m}</td>
            <td>{t.age_seconds}</td>
            <td>{(t.pump_probability * 100).toFixed(1)}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
