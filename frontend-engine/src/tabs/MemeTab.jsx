// src/tabs/MemeTab.jsx (or wherever your file lives)
import React, { useState, useEffect } from "react";

// With Vite, env variables are read via import.meta.env and must start with VITE_
const API = import.meta.env.VITE_BACKEND_HTTP || "http://localhost:4000";

export default function MemeTab() {
  const [signals, setSignals] = useState([]);
  const [minConf, setMinConf] = useState(0.8);

  useEffect(() => {
    // fetch meme signals with confidence filter
    fetch(`${API}/api/meme-signals?min_conf=${minConf}&limit=200`)
      .then((r) => r.json())
      .then((rows) => setSignals(rows))
      .catch((err) => {
        console.error("[MemeTab] fetch error:", err);
      });
  }, [minConf]);
function fmt(x, digits = 3) {
  const n = Number(x);
  return isNaN(n) ? "—" : n.toFixed(digits);
}

  return (
    <div className="card">
      <header className="card-header">
        <h2>AI Meme Coin Alpha</h2>
        <div className="controls">
          <label>
            Min confidence:
            <input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={minConf}
              onChange={(e) =>
                setMinConf(
                  Math.min(
                    1,
                    Math.max(0, parseFloat(e.target.value) || 0)
                  )
                )
              }
            />
          </label>
        </div>
      </header>

      <table className="signals-table">
        <thead>
          <tr>
            <th>Coin</th>
            <th>Trend</th>
            <th>Social</th>
            <th>Momentum</th>
            <th>Alpha</th>
            <th>Direction</th>
            <th>Confidence</th>
          </tr>
        </thead>
       <tbody>
  {signals.map((s) => (
    <tr key={s.id || `${s.symbol}-${s.created_at}`}>
      <td>{s.symbol}</td>
      <td>{fmt(s.trend_score)}</td>
      <td>{fmt(s.social_score)}</td>
      <td>{fmt(s.momentum)}</td>
      <td>{fmt(s.alpha)}</td>

      <td>
        {s.direction === "BUY"  && <button className="pill pill-buy">BUY</button>}
        {s.direction === "SELL" && <button className="pill pill-sell">SELL</button>}
        {s.direction === "HOLD" && <button className="pill pill-hold">HOLD</button>}
      </td>

      <td>
        {fmt(Number(s.confidence) * 100, 1) + "%"}
      </td>
    </tr>
  ))}

  {!signals.length && (
    <tr><td colSpan={7} style={{ textAlign: "center" }}>No results</td></tr>
  )}
</tbody>

      </table>
    </div>
  );
}
