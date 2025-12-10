// src/tabs/SettingsTab.jsx
import React, { useEffect, useState } from "react";

const STORAGE_KEY = "pauda_dashboard_settings_v1";

const defaultSettings = {
  // Core / Meme Signals
  coreSignals: {
    minScore: 0.7,
    maxLatencySec: 60,
    maxRows: 200,
    autoRefreshSec: 30,
  },
  memeSignals: {
    minMcap: 50000,
    minVolume5m: 1000,
    minBuys5m: 3,
    maxAgeHours: 48,
  },

  // PumpX Radar
  pumpxRadar: {
    minProbability: 0.6,
    minMcap: 4000,
    minVolume5m: 0,
    minBuys1h: 50,
    minPriceChange1hPct: 30,
    maxAgeDays: 3,
    maxRows: 500,
    autoRefreshSec: 20,
  },

  // PumpX Trends
  pumpxTrends: {
    minTrendScore: 0.6,
    lookbackHours: 24,
    maxTrendRows: 200,
  },

  // PumpX Alerts
  pumpxAlerts: {
    minAlertScore: 0.75,
    minPriceSpikePct: 25,
    minVolumeSpikeX: 3,
    alertCooldownMin: 10,
    enableSound: false,
    enableDesktop: false,
  },

  // UI / Misc
  ui: {
    theme: "dark",
    enableAnimations: true,
    autoScrollLogs: true,
  },
};

function loadSettings() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultSettings;
    const parsed = JSON.parse(raw);

    return {
      ...defaultSettings,
      ...parsed,
      coreSignals: {
        ...defaultSettings.coreSignals,
        ...(parsed.coreSignals || {}),
      },
      memeSignals: {
        ...defaultSettings.memeSignals,
        ...(parsed.memeSignals || {}),
      },
      pumpxRadar: {
        ...defaultSettings.pumpxRadar,
        ...(parsed.pumpxRadar || {}),
      },
      pumpxTrends: {
        ...defaultSettings.pumpxTrends,
        ...(parsed.pumpxTrends || {}),
      },
      pumpxAlerts: {
        ...defaultSettings.pumpxAlerts,
        ...(parsed.pumpxAlerts || {}),
      },
      ui: {
        ...defaultSettings.ui,
        ...(parsed.ui || {}),
      },
    };
  } catch {
    return defaultSettings;
  }
}

function saveSettings(settings) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export default function SettingsTab() {
  const [settings, setSettings] = useState(defaultSettings);
  const [savedAt, setSavedAt] = useState(null);

  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  function updateSection(section, field, value) {
    setSettings((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value,
      },
    }));
  }

  function handleSave() {
    saveSettings(settings);
    setSavedAt(new Date().toLocaleString());
  }

  function handleReset() {
    setSettings(defaultSettings);
    saveSettings(defaultSettings);
    setSavedAt(new Date().toLocaleString() + " (reset)");
  }

  // (Rendering is unchanged from your current version – keep your JSX here)
  // If you want I can paste the full render as well, but the key fixes
  // are loadSettings / updateSection above.
  // ------------------------------------------------------------

  // For brevity, I’ll assume you keep your existing JSX body here.
  // ------------------------------------------------------------
  return (
    <div style={{ padding: 24, color: "#f5f5f5" }}>
      {/* ... your existing sections markup (coreSignals, memeSignals,
           pumpxRadar, pumpxTrends, pumpxAlerts, ui) ... */}
      {/* Keep the inputs but make sure they call updateSection as before */}

      {/* At the very end, “Save” / “Reset” buttons and savedAt label */}
      <div style={{ marginTop: 16 }}>
        <button onClick={handleSave} style={{ marginRight: 8 }}>
          Save Settings
        </button>
        <button onClick={handleReset}>Reset to Defaults</button>
        {savedAt && (
          <span style={{ marginLeft: 12, fontSize: 11, opacity: 0.7 }}>
            Last saved: {savedAt}
          </span>
        )}
      </div>
    </div>
  );
}
