// frontend-engine/src/components/Tabs.jsx
import React from "react";

export default function Tabs({ active, onChange }) {
  const items = [
    { id: "core",             label: "Core Signals" },
    { id: "meme",             label: "Meme Signals" },
    { id: "pumpx",            label: "PumpX Radar" },
    { id: "pumpx-ml",         label: "PumpX ML Panel" },
    { id: "pumpx-alerts",     label: "PumpX Alerts Panel" },
    { id: "pumpx-trends",     label: "PumpX Trends" },
    { id: "pumpx-hourlychart", label: "PumpX Hourly chart OHLC" },
    { id: "settings",         label: "Dashboard Settings" },
  ];

  return (
    <div className="tabs">
      {items.map((t) => (
        <button
          key={t.id}
          type="button"
          className={`tab ${active === t.id ? "active" : ""}`}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
