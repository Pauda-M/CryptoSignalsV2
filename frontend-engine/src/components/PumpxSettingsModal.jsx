import React from "react";
import { usePumpxSettings } from "../context/PumpxSettingsContext";

export default function PumpxSettingsModal({ isOpen, onClose }) {
  const { settings, updateSettings, resetSettings } = usePumpxSettings();

  if (!isOpen) return null;

  const setRadar = (field, v) =>
    updateSettings({ radar: { ...settings.radar, [field]: v } });

  const setAlerts = (field, v) =>
    updateSettings({ alerts: { ...settings.alerts, [field]: v } });

  const setTrends = (field, v) =>
    updateSettings({ trends: { ...settings.trends, [field]: v } });

  return (
    <div className="modal-overlay">
      <div className="modal-card">
        <h2>PumpX Settings</h2>

        <h3>Radar Filters</h3>
        <label>
          Min MCAP:
          <input
            type="number"
            value={settings.radar.minMcap}
            onChange={(e) => setRadar("minMcap", Number(e.target.value))}
          />
        </label>

        <label>
          Min Buys (1h):
          <input
            type="number"
            value={settings.radar.minBuys1h}
            onChange={(e) => setRadar("minBuys1h", Number(e.target.value))}
          />
        </label>

        <label>
          Min Pump 1h %:
          <input
            type="number"
            value={settings.radar.minPump1hPct}
            onChange={(e) => setRadar("minPump1hPct", Number(e.target.value))}
          />
        </label>

        <hr />

        <h3>Pump Alerts</h3>
        <label>
          Min % Price Change:
          <input
            type="number"
            value={settings.alerts.minPriceChangePct}
            onChange={(e) => setAlerts("minPriceChangePct", Number(e.target.value))}
          />
        </label>

        <label>
          Min Buys (5m):
          <input
            type="number"
            value={settings.alerts.minBuys5m}
            onChange={(e) => setAlerts("minBuys5m", Number(e.target.value))}
          />
        </label>

        <label>
          Min Pump Probability:
          <input
            type="number"
            step="0.05"
            value={settings.alerts.minPumpProb}
            onChange={(e) => setAlerts("minPumpProb", Number(e.target.value))}
          />
        </label>

        <hr />

        <h3>Trend Ranking</h3>
        <label>
          Momentum Weight
          <input
            type="number"
            step="0.1"
            value={settings.trends.momentumWeight}
            onChange={(e) => setTrends("momentumWeight", Number(e.target.value))}
          />
        </label>
        <label>
          Volatility Weight
          <input
            type="number"
            step="0.1"
            value={settings.trends.volatilityWeight}
            onChange={(e) => setTrends("volatilityWeight", Number(e.target.value))}
          />
        </label>
        <label>
          Pump Trend Weight
          <input
            type="number"
            step="0.1"
            value={settings.trends.pumpTrendWeight}
            onChange={(e) => setTrends("pumpTrendWeight", Number(e.target.value))}
          />
        </label>

        <div className="modal-buttons">
          <button onClick={resetSettings}>Reset to Defaults</button>
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
