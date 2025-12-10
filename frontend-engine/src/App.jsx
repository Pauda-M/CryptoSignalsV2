// frontend-engine/src/App.jsx
import React, { useState } from "react";
import Tabs from "./components/Tabs.jsx";

import CoreSignalsTab from "./tabs/SignalsTab.jsx";
import MemeTab from "./tabs/MemeTab.jsx";
import PumpxRadarTab from "./tabs/PumpxTab.jsx";
import PumpxMLTab from "./tabs/PumpxMLTab.jsx";
import PumpxAlertsTab from "./tabs/PumpxAlertsTab.jsx";
import PumpxTrendsTab from "./tabs/PumpxTrendsTab.jsx";
import PumpxHourlychartTab from "./tabs/PumpxHourlychartTab.jsx";
import SettingsTab from "./tabs/SettingsTab.jsx";

export default function App() {
  const [tab, setTab] = useState("core");

  return (
    <div className="app">
      <header className="app-header">
        <h1>Crypto AI Trading Dashboard</h1>
        <p>AI & ML based signal hunter and whale copy trader</p>
      </header>

      <Tabs active={tab} onChange={setTab} />

      <main className="app-content">
        {tab === "core" && <CoreSignalsTab />}
        {tab === "meme" && <MemeTab />}
        {tab === "pumpx" && <PumpxRadarTab />}
        {tab === "pumpx-ml" && <PumpxMLTab />}
        {tab === "pumpx-alerts" && <PumpxAlertsTab />}
        {tab === "pumpx-trends" && <PumpxTrendsTab />}
        {tab === "pumpx-hourlychart" && <PumpxHourlychartTab />}
        {tab === "settings" && <SettingsTab />}
      </main>
    </div>
  );
}
