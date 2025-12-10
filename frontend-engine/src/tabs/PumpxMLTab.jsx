// frontend-engine/src/tabs/PumpxMLTab.jsx
import React, { useState } from "react";

export default function PumpxMLTab() {
  const [log, setLog] = useState("");

  function clearLog() {
    setLog("");
  }

  async function run(path) {
    try {
      setLog((prev) => prev + `\n[CMD] === Running ${path.toUpperCase()} ===\n`);

      const response = await fetch(`/api/ml/${path}`);
      if (!response.body) {
        setLog((prev) => prev + "\n[ERR] No response body.\n");
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        setLog((prev) => prev + chunk);
      }

      setLog((prev) => prev + "\n[OK] Done.\n");
    } catch (err) {
      console.error(err);
      setLog((prev) => prev + `\n[ERR] ${String(err)}\n`);
    }
  }

  return (
    <div className="card">
      <h2>PumpX ML Training Panel</h2>
      <p>Build training dataset, train the XGBoost model, and (optionally) deploy it.</p>

      <div style={{ marginTop: 12, marginBottom: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button onClick={() => run("build")}>Build Dataset</button>
        <button onClick={() => run("train")}>Train Model</button>
        <button onClick={() => run("deploy")}>Deploy Model</button>
        <button onClick={clearLog}>Clear Log</button>
      </div>

      <pre
        style={{
          marginTop: "12px",
          height: "450px",
          background: "#000",
          color: "#0f0",
          padding: "10px",
          overflowY: "scroll",
          border: "1px solid #444",
          fontSize: "12px",
        }}
      >
        {log || "[LOG] Waiting for commands..."}
      </pre>
    </div>
  );
}
