import React, { useEffect, useState } from "react";

const API = import.meta.env.VITE_BACKEND_HTTP || "http://localhost:4000";

export default function PortfolioTab() {
  const [portfolios, setPortfolios] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [portfolioDetail, setPortfolioDetail] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/portfolios`)
      .then((r) => r.json())
      .then((data) => {
        setPortfolios(data);
        if (data.length && !selectedId) {
          setSelectedId(data[0].id);
        }
      })
      .catch((err) => console.error("portfolios fetch error", err));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setLoadingDetail(true);

    Promise.all([
      fetch(`${API}/api/portfolios/${selectedId}`).then((r) => r.json()),
      fetch(`${API}/api/quant/portfolio/${selectedId}/latest`).then((r) =>
        r.ok ? r.json() : null
      )
    ])
      .then(([p, m]) => {
        setPortfolioDetail(p);
        setMetrics(m);
      })
      .catch((err) => console.error("portfolio detail fetch error", err))
      .finally(() => setLoadingDetail(false));
  }, [selectedId]);

  return (
    <div className="portfolio-layout">
      <aside className="portfolio-list card">
        <h2>Portfolios</h2>
        <ul>
          {portfolios.map((p) => (
            <li key={p.id}>
              <button
                className={
                  p.id === selectedId ? "portfolio-item active" : "portfolio-item"
                }
                onClick={() => setSelectedId(p.id)}
              >
                <div className="portfolio-name">{p.name}</div>
                <div className="portfolio-sub">
                  Base: {p.base_currency} · ID: {p.id}
                </div>
              </button>
            </li>
          ))}
          {!portfolios.length && (
            <li className="portfolio-empty">
              No portfolios yet. Use API / Telegram to create one.
            </li>
          )}
        </ul>
      </aside>

      <section className="portfolio-detail card">
        {loadingDetail && <div>Loading...</div>}
        {!loadingDetail && portfolioDetail && (
          <>
            <h2>{portfolioDetail.portfolio.name}</h2>
            <p className="muted">
              Base currency: {portfolioDetail.portfolio.base_currency}
            </p>

            {metrics ? (
              <div className="metrics-grid">
                <MetricCard
                  label="Total Return"
                  value={metrics.total_return}
                  format="percent"
                />
                <MetricCard
                  label="Annualized Return"
                  value={metrics.annualized_return}
                  format="percent"
                />
                <MetricCard
                  label="Volatility"
                  value={metrics.volatility}
                  format="percent"
                />
                <MetricCard
                  label="Sharpe"
                  value={metrics.sharpe_ratio}
                  format="number"
                />
                <MetricCard
                  label="Sortino"
                  value={metrics.sortino_ratio}
                  format="number"
                />
                <MetricCard
                  label="Max Drawdown"
                  value={metrics.max_drawdown}
                  format="percent"
                />
                <MetricCard
                  label="VaR 95% (1d)"
                  value={metrics.var_95}
                  format="percent"
                />
                <MetricCard
                  label="Concentration"
                  value={metrics.concentration_index}
                  format="number"
                />
              </div>
            ) : (
              <p className="muted">
                No quant snapshot yet. Wait for quant-engine to run.
              </p>
            )}

            <h3>Positions</h3>
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Quantity</th>
                  <th>Avg Entry</th>
                </tr>
              </thead>
              <tbody>
                {portfolioDetail.positions.map((pos) => (
                  <tr key={pos.id}>
                    <td>{pos.symbol}</td>
                    <td>{pos.quantity}</td>
                    <td>{pos.avg_entry_price ?? "-"}</td>
                  </tr>
                ))}
                {!portfolioDetail.positions.length && (
                  <tr>
                    <td colSpan="3" style={{ textAlign: "center" }}>
                      No positions in this portfolio.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </>
        )}
      </section>
    </div>
  );
}

function MetricCard({ label, value, format }) {
  let text = "—";

  if (typeof value === "number" && !Number.isNaN(value)) {
    if (format === "percent") {
      text = (value * 100).toFixed(2) + "%";
    } else {
      text = value.toFixed(2);
    }
  }

  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{text}</div>
    </div>
  );
}
