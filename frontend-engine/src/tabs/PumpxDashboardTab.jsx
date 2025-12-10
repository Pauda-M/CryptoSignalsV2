// src/tabs/PumpxDashboardTab.jsx
import React, { useEffect, useMemo, useState } from "react";

const STREAMER_URL =
  import.meta.env.VITE_PUMPX_STREAMER || "ws://localhost:4101";
const LS_KEY = "pumpx_radar_filters_v1";

const defaultFilters = {
  minMcap: 5000,      // USD
  minBuys1h: 10,      // buys in last 1h
  minPump1h: 0,       // 1h price change %
  maxAgeDays: 10,     // 0 = off
  mlOnly: false,      // require pump_probability
};

function loadFilters() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return defaultFilters;
    const parsed = JSON.parse(raw);
    return { ...defaultFilters, ...parsed };
  } catch {
    return defaultFilters;
  }
}

const thStyle = {
  padding: "6px 8px",
  textAlign: "left",
  fontSize: 12,
  fontWeight: 600,
};

const tdStyle = {
  padding: "4px 8px",
  fontSize: 12,
  borderTop: "1px solid #111",
};

export default function PumpxDashboardTab() {
  const [tokens, setTokens] = useState([]);
  const [filters, setFilters] = useState(loadFilters);
  const [selectedMint, setSelectedMint] = useState(null);
  const [wsStatus, setWsStatus] = useState("connecting");

  // WebSocket subscription
  useEffect(() => {
    let ws;
    let reconnectTimer;

    const connect = () => {
      ws = new WebSocket(STREAMER_URL);

      ws.onopen = () => {
        console.log("[PumpX Radar] Connected to streamer:", STREAMER_URL);
        setWsStatus("connected");
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "snapshot" && Array.isArray(msg.data)) {
            setTokens(msg.data);
          }
        } catch (err) {
          console.error("[PumpX Radar] invalid WS message", err);
        }
      };

      ws.onerror = (err) => {
        console.error("[PumpX Radar] WS error:", err);
      };

      ws.onclose = () => {
        console.warn("[PumpX Radar] disconnected – retrying");
        setWsStatus("disconnected");
        reconnectTimer = setTimeout(connect, 1500);
      };
    };

    connect();

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, []);

  // Persist filters
  useEffect(() => {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(filters));
    } catch {
      /* ignore */
    }
  }, [filters]);

  // Normalised + filtered data
  const filteredTokens = useMemo(() => {
    return (tokens || [])
      .map((t) => {
        const price = Number(t.price) || 0;
        const marketcap = Number(t.marketcap) || 0;
        const volume5m = Number(t.volume_5m) || 0;
        const buys5m = Number(t.buys_5m) || 0;
        const sells5m = Number(t.sells_5m) || 0;
        const buys1h = Number(t.buys_1h ?? t.buys1h ?? 0) || 0;

        const pumpProb =
          t.pump_probability !== null && t.pump_probability !== undefined
            ? Number(t.pump_probability)
            : null;

        const priceChange1h = Number(t.price_change_1h ?? 0); // 0–1 fraction
        const pump1hPct =
          priceChange1h > 2 ? priceChange1h : priceChange1h * 100;

        const ageSeconds = Number(t.age_seconds ?? 0);
        const ageMinutes =
          ageSeconds > 0
            ? ageSeconds / 60
            : Number(t.age_minutes ?? t.age_min ?? 0) || 0;
        const ageDays = ageMinutes / 60 / 24;

        return {
          ...t,
          price,
          marketcap,
          volume5m,
          buys5m,
          sells5m,
          buys1h,
          pumpProb,
          pump1hPct,
          ageMinutes,
          ageDays,
        };
      })
      .filter((t) => {
        if (t.marketcap < filters.minMcap) return false;
        if (t.buys1h < filters.minBuys1h) return false;
        if (t.pump1hPct < filters.minPump1h) return false;

        if (filters.maxAgeDays > 0 && t.ageDays > filters.maxAgeDays) {
          return false;
        }

        if (filters.mlOnly && (t.pumpProb === null || t.pumpProb <= 0)) {
          return false;
        }

        return true;
      })
      .sort((a, b) => {
        const pa = a.pumpProb ?? 0;
        const pb = b.pumpProb ?? 0;
        if (pb !== pa) return pb - pa;
        if (b.marketcap !== a.marketcap) return b.marketcap - a.marketcap;
        return b.volume5m - a.volume5m;
      });
  }, [tokens, filters]);

  // Simple trend score for “Top Trending” section
  const trending = useMemo(() => {
    return filteredTokens
      .map((t) => {
        const buyPressure = t.buys5m - t.sells5m;
        const trendScore =
          (t.pumpProb ?? 0) * 100 + // base on ML score
          t.pump1hPct * 0.5 + // reward 1h price move
          buyPressure * 0.5 + // net buys
          t.volume5m / 1000; // scale with volume a bit

        return { ...t, trendScore };
      })
      .sort((a, b) => b.trendScore - a.trendScore)
      .slice(0, 20);
  }, [filteredTokens]);

  const rawCount = tokens.length;
  const filteredCount = filteredTokens.length;

  const handleResetFilters = () => {
    setFilters(defaultFilters);
  };

  const handleRowClick = (mint) => {
    setSelectedMint(mint);
  };

  return (
    <div style={{ padding: 24, color: "#f5f5f5" }}>
      <h2 style={{ marginBottom: 8 }}>PumpX Radar</h2>
      <p style={{ marginTop: 0, opacity: 0.7 }}>
        Live Solana meme coins scored by PumpX ML.
      </p>
      <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>
        WS: {wsStatus} · raw: {rawCount}, filtered: {filteredCount}
        {selectedMint ? `, selected: ${selectedMint.slice(0, 6)}…` : ""}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 24,
          marginTop: 16,
        }}
      >
        {/* Main table */}
        <div style={{ flex: 3, minWidth: 0 }}>
          <div
            style={{
              borderRadius: 10,
              border: "1px solid #222",
              overflow: "hidden",
              background: "rgba(5,5,15,0.95)",
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
                  <th style={thStyle}>Symbol</th>
                  <th style={thStyle}>Mint</th>
                  <th style={thStyle}>Price</th>
                  <th style={thStyle}>MCAP</th>
                  <th style={thStyle}>Vol 5m</th>
                  <th style={thStyle}>Buys 5m</th>
                  <th style={thStyle}>Sells 5m</th>
                  <th style={thStyle}>Buys 1h</th>
                  <th style={thStyle}>Δ1h %</th>
                  <th style={thStyle}>Age (min)</th>
                  <th style={thStyle}>ML</th>
                  <th style={thStyle}>Updated</th>
                </tr>
              </thead>
              <tbody>
                {filteredTokens.length === 0 ? (
                  <tr>
                    <td
                      colSpan={12}
                      style={{
                        padding: 16,
                        textAlign: "center",
                        opacity: 0.7,
                      }}
                    >
                      No tokens matching filters.
                    </td>
                  </tr>
                ) : (
                  filteredTokens.map((t) => {
                    const pumpPct = t.pumpProb != null ? t.pumpProb * 100 : 0;
                    return (
                      <tr
                        key={t.mint}
                        onClick={() => handleRowClick(t.mint)}
                        style={{
                          cursor: "pointer",
                          background:
                            t.mint === selectedMint
                              ? "rgba(50,80,160,0.35)"
                              : "transparent",
                        }}
                      >
                        <td style={tdStyle}>{t.symbol || "?"}</td>
                        <td
                          style={{
                            ...tdStyle,
                            fontFamily: "monospace",
                            maxWidth: 220,
                            overflow: "hidden",
                          }}
                        >
                          {t.mint}
                        </td>
                        <td style={tdStyle}>{t.price.toExponential(4)}</td>
                        <td style={tdStyle}>{Math.round(t.marketcap)}</td>
                        <td style={tdStyle}>{Math.round(t.volume5m)}</td>
                        <td style={tdStyle}>{t.buys5m}</td>
                        <td style={tdStyle}>{t.sells5m}</td>
                        <td style={tdStyle}>{t.buys1h}</td>
                        <td style={tdStyle}>{t.pump1hPct.toFixed(1)}%</td>
                        <td style={tdStyle}>{t.ageMinutes.toFixed(0)}</td>
                        <td style={tdStyle}>
                          {t.pumpProb != null ? pumpPct.toFixed(1) + "%" : "-"}
                        </td>
                        <td style={tdStyle}>
                          {t.updated_at
                            ? String(t.updated_at).slice(11, 19)
                            : "-"}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Trending section */}
          <div style={{ marginTop: 24 }}>
            <h3 style={{ marginBottom: 8, fontSize: 16 }}>Top Trending</h3>
            <p style={{ marginTop: 0, fontSize: 12, opacity: 0.7 }}>
              Trend score is a blend of PumpX ML score, 1h price move, buy
              pressure, and 5m volume.
            </p>

            <div
              style={{
                borderRadius: 10,
                border: "1px solid #222",
                overflow: "hidden",
                background: "rgba(5,5,15,0.95)",
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
                        "linear-gradient(90deg, rgba(80,40,40,0.9), rgba(40,20,20,0.9))",
                    }}
                  >
                    <th style={thStyle}>#</th>
                    <th style={thStyle}>Symbol</th>
                    <th style={thStyle}>Mint</th>
                    <th style={thStyle}>Score</th>
                    <th style={thStyle}>ML%</th>
                    <th style={thStyle}>Δ1h %</th>
                    <th style={thStyle}>Buys-Sells (5m)</th>
                    <th style={thStyle}>Vol 5m</th>
                  </tr>
                </thead>
                <tbody>
                  {trending.length === 0 ? (
                    <tr>
                      <td
                        colSpan={8}
                        style={{
                          padding: 12,
                          textAlign: "center",
                          opacity: 0.7,
                        }}
                      >
                        No trending rows.
                      </td>
                    </tr>
                  ) : (
                    trending.map((t, idx) => {
                      const pumpPct =
                        t.pumpProb != null ? t.pumpProb * 100 : 0;
                      const buyPressure = t.buys5m - t.sells5m;
                      return (
                        <tr key={t.mint}>
                          <td style={tdStyle}>{idx + 1}</td>
                          <td style={tdStyle}>{t.symbol || "?"}</td>
                          <td
                            style={{
                              ...tdStyle,
                              fontFamily: "monospace",
                              maxWidth: 200,
                              overflow: "hidden",
                            }}
                          >
                            {t.mint}
                          </td>
                          <td style={tdStyle}>{t.trendScore.toFixed(2)}</td>
                          <td style={tdStyle}>
                            {t.pumpProb != null
                              ? pumpPct.toFixed(1) + "%"
                              : "-"}
                          </td>
                          <td style={tdStyle}>{t.pump1hPct.toFixed(1)}%</td>
                          <td style={tdStyle}>
                            {buyPressure > 0 ? "+" : ""}
                            {buyPressure}
                          </td>
                          <td style={tdStyle}>{Math.round(t.volume5m)}</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Filter panel */}
        <div
          style={{
            flex: "0 0 260px",
            borderRadius: 10,
            border: "1px solid #222",
            background: "rgba(10,10,20,0.96)",
            padding: 16,
            fontSize: 13,
          }}
        >
          <h4 style={{ marginTop: 0, marginBottom: 10 }}>Radar Filters</h4>

          <label style={{ display: "block", marginBottom: 6 }}>
            Min MCAP
            <input
              type="number"
              value={filters.minMcap}
              onChange={(e) =>
                setFilters((f) => ({
                  ...f,
                  minMcap: Number(e.target.value) || 0,
                }))
              }
              style={{ width: "100%" }}
            />
          </label>

          <label style={{ display: "block", marginBottom: 6 }}>
            Min Buys 1h
            <input
              type="number"
              value={filters.minBuys1h}
              onChange={(e) =>
                setFilters((f) => ({
                  ...f,
                  minBuys1h: Number(e.target.value) || 0,
                }))
              }
              style={{ width: "100%" }}
            />
          </label>

          <label style={{ display: "block", marginBottom: 6 }}>
            Min Δ1h %
            <input
              type="number"
              value={filters.minPump1h}
              onChange={(e) =>
                setFilters((f) => ({
                  ...f,
                  minPump1h: Number(e.target.value) || 0,
                }))
              }
              style={{ width: "100%" }}
            />
          </label>

          <label style={{ display: "block", marginBottom: 6 }}>
            Max age (days, 0 = off)
            <input
              type="number"
              value={filters.maxAgeDays}
              onChange={(e) =>
                setFilters((f) => ({
                  ...f,
                  maxAgeDays: Number(e.target.value) || 0,
                }))
              }
              style={{ width: "100%" }}
            />
          </label>

          <label style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <input
              type="checkbox"
              checked={filters.mlOnly}
              onChange={(e) =>
                setFilters((f) => ({ ...f, mlOnly: e.target.checked }))
              }
            />
            Require ML probability
          </label>

          <button
            type="button"
            onClick={handleResetFilters}
            style={{ marginTop: 10, width: "100%" }}
          >
            Reset Filters
          </button>
        </div>
      </div>
    </div>
  );
}
