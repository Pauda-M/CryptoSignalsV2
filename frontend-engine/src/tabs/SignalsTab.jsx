import React, { useEffect, useState } from "react";

const REFRESH_MS = 5000;

export default function SignalsTab() {
  const [rows, setRows] = useState([]);
  const [minConf, setMinConf] = useState(0.6);
  const [minAlpha, setMinAlpha] = useState(2.0);
  const [loading, setLoading] = useState(false);

  const loadSignals = async () => {
    try {
      setLoading(true);

      const resp = await fetch(
        `/api/pumpx/alpha?min_confidence=${minConf}&min_alpha=${minAlpha}`
      );
      const data = await resp.json();

      setRows(data);
    } catch (err) {
      console.error("[PumpX] Error loading alpha signals:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSignals();
    const id = setInterval(loadSignals, REFRESH_MS);
    return () => clearInterval(id);
  }, [minConf, minAlpha]);

  const directionColor = (dir) => {
    if (dir === "LONG") return "#4ade80";
    if (dir === "SHORT") return "#f87171";
    return "#e5e5e5";
  };

  return (
    <div style={{ padding: 24, color: "#f5f5f5" }}>
      <h2 style={{ marginBottom: 8 }}>AI Meme Coin Alpha</h2>
      <p style={{ marginTop: 0, opacity: 0.7 }}>
        Realtime ML-powered alpha: trend score, momentum, buy pressure, 1h move.
      </p>

      {/* Filter Bar */}
      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <label style={{ fontSize: 13 }}>
          Min confidence (%):
          <input
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={minConf}
            onChange={(e) => setMinConf(Number(e.target.value) || 0)}
            style={{
              marginLeft: 8,
              width: 70,
              padding: "4px 6px",
              background: "#050510",
              border: "1px solid #333",
              color: "#fff",
              borderRadius: 4,
            }}
          />
        </label>

        <label style={{ fontSize: 13 }}>
          Min Alpha Score:
          <input
            type="number"
            value={minAlpha}
            step="0.5"
            onChange={(e) => setMinAlpha(Number(e.target.value) || 0)}
            style={{
              marginLeft: 8,
              width: 70,
              padding: "4px 6px",
              background: "#050510",
              border: "1px solid #333",
              color: "#fff",
              borderRadius: 4,
            }}
          />
        </label>

        <button
          onClick={loadSignals}
          style={{
            marginLeft: "auto",
            padding: "6px 12px",
            background:
              "linear-gradient(90deg, rgb(88,118,255), rgb(155,88,255))",
            border: "none",
            borderRadius: 8,
            cursor: "pointer",
            color: "#fff",
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          Refresh
        </button>
      </div>

      {/* Table */}
      <div
        style={{
          borderRadius: 10,
          border: "1px solid #222",
          overflow: "hidden",
          background: "rgba(5,5,15,0.96)",
        }}
      >
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 12,
          }}
        >
          <thead>
            <tr
              style={{
                background:
                  "linear-gradient(90deg, rgba(40,40,80,0.9), rgba(20,20,40,0.9))",
              }}
            >
              <th style={th}>Token</th>
              <th style={th}>Alpha</th>
              <th style={th}>Direction</th>
              <th style={th}>ML%</th>
              <th style={th}>Δ1h%</th>
              <th style={th}>Buys-Sells</th>
              <th style={th}>Vol 5m</th>
              <th style={th}>Updated</th>
            </tr>
          </thead>

          <tbody>
            {loading && rows.length === 0 ? (
              <tr>
                <td colSpan={8} style={empty}>
                  Loading…
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={8} style={empty}>
                  No signals for selected filters
                </td>
              </tr>
            ) : (
              rows.map((r) => {
                const mintShort = r.mint
                  ? r.mint.slice(0, 4) + "…" + r.mint.slice(-4)
                  : "?";

                return (
                  <tr key={r.mint}>
                    <td style={td}>
                      <div style={{ fontWeight: 600 }}>{r.symbol || "?"}</div>
                      <div
                        style={{
                          opacity: 0.6,
                          fontFamily: "monospace",
                          fontSize: 11,
                        }}
                      >
                        {mintShort}
                      </div>
                    </td>

                    <td style={td}>{r.alpha_score?.toFixed(2)}</td>

                    <td
                      style={{
                        ...td,
                        fontWeight: 600,
                        color: directionColor(r.direction),
                      }}
                    >
                      {r.direction}
                    </td>

                    <td style={td}>
                      {r.ml_confidence_pct?.toFixed(1)}%
                    </td>

                    <td style={td}>
                      {r.price_change_1h_pct?.toFixed(1)}%
                    </td>

                    <td style={td}>{r.buy_pressure_5m}</td>

                    <td style={td}>{Math.round(r.volume_5m)}</td>

                    <td style={td}>
                      {new Date(r.updated_at).toLocaleTimeString()}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const th = {
  padding: "6px 8px",
  textAlign: "left",
  borderBottom: "1px solid #222",
  fontWeight: 600,
};

const td = {
  padding: "6px 8px",
  borderBottom: "1px solid #151515",
  whiteSpace: "nowrap",
};

const empty = {
  padding: 16,
  textAlign: "center",
  opacity: 0.7,
};
