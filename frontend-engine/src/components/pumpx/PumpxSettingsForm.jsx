import React from "react";

export default function PumpxSettingsForm({ settings, setSettings }) {
  async function save() {
    await fetch("/api/ml/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    alert("Saved settings");
  }

  return (
    <div className="pumpx-settings">
      <h3>Training Parameters</h3>

      <label>Horizon (min)</label>
      <input
        type="number"
        value={settings.horizon_minutes}
        onChange={(e) =>
          setSettings({
            ...settings,
            horizon_minutes: Number(e.target.value),
          })
        }
      />

      <label>Pump threshold</label>
      <input
        type="number"
        step="0.01"
        value={settings.pump_threshold}
        onChange={(e) =>
          setSettings({
            ...settings,
            pump_threshold: Number(e.target.value),
          })
        }
      />

      <label>Min MC for training labels</label>
      <input
        type="number"
        value={settings.min_mc}
        onChange={(e) =>
          setSettings({
            ...settings,
            min_mc: Number(e.target.value),
          })
        }
      />

      <button onClick={save}>Save</button>
    </div>
  );
}
