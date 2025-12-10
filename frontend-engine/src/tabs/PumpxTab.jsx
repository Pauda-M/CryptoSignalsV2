// frontend-engine/src/tabs/PumpxTab.jsx
import React, { useEffect, useState } from "react";
import { getLive } from "../services/pumpxApi.js";

function loadSettings() {
  try {
    const raw = localStorage.getItem("pauda_dashboard_settings_v1");
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export default function PumpxRadarTab() {
  const [rows, setRows] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // local filter state (defaults from settings if present)
  const settings = loadSettings();
  const [minProb, setMinProb] = useState(
    settings?.pumpxRadar?.minProbability ?? 0.6
  );
  const [minMcap, setMinMcap] = useState(settings?.pumpxRadar?.minMcap ?? 4000);
  const [minBuys1h, setMinBuys1h] = useState(
    settings?.pumpxRadar?.minBuys1h ?? 20
  );
  const [minChange1h, setMinChange1h] = useState(
    settings?.pumpxRadar?.minPriceChange1hPct ?? 10
  );
  const [autoRefreshSec, setAutoRefreshSec] = useState(
    settings?.pumpxRadar?.autoRefreshSec ?? 20
  );

  function applyFilters(data) {
    return data.filter((row) => {
      const prob = row.pump_probability ?? 0;
      const mcap = Number(row.marketcap ?? 0);
      const buys1h = row.buys_1h ?? 0;
      const pc1h = (row.price_change_1h ?? 0) * 100;

      if (prob < minProb) return false;
      if (mcap < minMcap) return false;
      if (buys1h < minBuys1h) return false;
      if (pc1h < minChange1h) return false;
      return true;
    });
  }

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const data = await getLive();
      setRows(data);
      setFiltered(applyFilters(data));
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error(err);
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  // first load
  useEffect(() => {
    loadData();
  }, []);

  // refilter when thresholds change
  useEffect(() => {
    setFiltered(applyFilters(rows));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [minProb, minMcap, minBuys1h, minChange1h, rows]);

  // auto-refresh
  useEffect(() => {
    if (!autoRefreshSec || autoRefreshSec <= 0) return;
    const ms = autoRefreshSec * 1000;
    const id = setInterval(loadData, ms);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefreshSec]);

  function openDex(mint) {
    if (!mint) return;
    const url = `https://dexscreener.com/solana/${mint}`;
    window.open(url, "_blank", "noopener,noreferrer");
  }

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">PumpX Radar</div>
          <div className="card-subtitle">
            Live Pump.fun tokens with ML probability &amp; on-chain metrics.
          </div>
        </div>
        <div style={{ fontSize: 12, textAlign: "right" }}>
          <div>Raw: {rows.length}</div>
          <div>Filtered: {filtered.length}</div>
          {lastUpdated && <div>Updated: {lastUpdated}</div>}
        </div>
      </div>

      <div className="filters-panel">
        <label>
          Min ML prob
          <input
            type="number"
            step="0.01"
            value={minProb}
            onChange={(e) => setMinProb(parseFloat(e.target.value) || 0)}
          />
        </label>
        <label>
          Min mcap
          <input
            type="number"
            value={minMcap}
            onChange={(e) => setMinMcap(parseFloat(e.target.value) || 0)}
          />
        </label>
        <label>
          Min buys 1h
          <input
            type="number"
            value={minBuys1h}
            onChange={(e) => setMinBuys1h(parseInt(e.target.value || "0", 10))}
          />
        </label>
        <label>
          Min Δ1h (%)
          <input
            type="number"
            value={minChange1h}
            onChange={(e) =>
              setMinChange1h(parseFloat(e.target.value || "0"))
            }
          />
        </label>
        <label>
          Auto-refresh (sec)
          <input
            type="number"
            value={autoRefreshSec}
            onChange={(e) =>
              setAutoRefreshSec(parseInt(e.target.value || "0", 10))
            }
          />
        </label>
        <button onClick={loadData} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh now"}
        </button>
      </div>

      {error && (
        <div className="error-banner">
          Error loading PumpX Radar: {error}
        </div>
      )}

      <div className="table-wrapper">
        <table className="table">
          <thead>
            <tr>
              <th>Token</th>
              <th>MCAP</th>
              <th>Price</th>
              <th>Vol 5m</th>
              <th>Buys 5m</th>
              <th>Sells 5m</th>
              <th>Buys 1h</th>
              <th>Sells 1h</th>
              <th>Δ1h %</th>
              <th>ML prob</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row) => {
              const pc1h = (row.price_change_1h ?? 0) * 100;
              const prob = (row.pump_probability ?? 0) * 100;
              return (
                <tr
                  key={row.token_id}
                  onClick={() => openDex(row.mint)}
                  style={{ cursor: "pointer" }}
                >
                  <td>
                    <div>{row.symbol || "-"}</div>
                    <div style={{ fontSize: 11, opacity: 0.7 }}>
                      {row.name || row.mint}
                    </div>
                  </td>
                  <td>{Number(row.marketcap ?? 0).toFixed(0)}</td>
                  <td>{Number(row.price ?? 0).toExponential(2)}</td>
                  <td>{Number(row.volume_5m ?? 0).toFixed(2)}</td>
                  <td>{row.buys_5m ?? 0}</td>
                  <td>{row.sells_5m ?? 0}</td>
                  <td>{row.buys_1h ?? 0}</td>
                  <td>{row.sells_1h ?? 0}</td>
                  <td
                    style={{
                      color: pc1h >= 0 ? "#4ade80" : "#f97373",
                    }}
                  >
                    {pc1h.toFixed(2)}
                  </td>
                  <td>{prob.toFixed(1)}%</td>
                  <td style={{ fontSize: 11 }}>
                    {row.updated_at
                      ? new Date(row.updated_at).toLocaleTimeString()
                      : "-"}
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={11} style={{ textAlign: "center", opacity: 0.7 }}>
                  No tokens match current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
