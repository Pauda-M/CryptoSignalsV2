import React from "react";

export default function PumpxPerformanceBox({ perf }) {
  if (!perf) return <div>Loading performance...</div>;

  return (
    <div className="pumpx-perf-box">
      <h4>Model Performance (Last 24h)</h4>
      <ul>
        <li>Total Predictions: {perf.total_predictions}</li>
        <li>
          Avg future return ({perf.horizon_minutes}m):{" "}
          {(perf.avg_future_return * 100).toFixed(2)}%
        </li>
        <li>
          High confidence (> {perf.high_conf_threshold * 100}%):{" "}
          {perf.high_conf_count}
        </li>
        <li>
          Pump accuracy: {(perf.high_conf_pump_rate * 100).toFixed(1)}%
        </li>
      </ul>
    </div>
  );
}
