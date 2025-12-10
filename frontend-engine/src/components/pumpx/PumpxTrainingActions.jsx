import React from "react";

export default function PumpxTrainingActions({ setLog }) {
  async function run(endpoint) {
    const res = await fetch(`/api/ml/${endpoint}`, { method: "POST" });
    const data = await res.json();
    setLog(data.log || data.error || "Done.");
  }

  return (
    <div>
      <h3>Training Actions</h3>

      <button onClick={() => run("build")}>Build Dataset</button>
      <button onClick={() => run("train")}>Train Model</button>
      <button onClick={() => run("deploy")}>Deploy Model</button>
    </div>
  );
}
