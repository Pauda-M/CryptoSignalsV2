import React, { useEffect, useState } from "react";

const API = import.meta.env.VITE_BACKEND_HTTP || "http://localhost:4000";

export default function SignalTable() {
  const [rows, setRows] = useState([]);

  useEffect(() => {
    fetch(`${API}/api/signals`)
      .then((r) => r.json())
      .then((data) => setRows(data))
      .catch(() => {});
  }, []);

  return (
    <div className="card">
      <h2>Core Signals</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Timeframe</th>
            <th>Direction</th>
            <th>Confidence</th>
            <th>Entry</th>
            <th>Stop</th>
            <th>Take Profit</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{r.symbol}</td>
              <td>{r.timeframe}</td>
              <td>{r.direction}</td>
              <td>{Math.round(r.confidence * 100)}%</td>
              <td>{r.entry_price}</td>
              <td>{r.stop_loss}</td>
              <td>{r.take_profit}</td>
              <td>{new Date(r.created_at).toLocaleTimeString()}</td>
            </tr>
          ))}
          {!rows.length && (
            <tr>
              <td colSpan="8" style={{ textAlign: "center" }}>
                No core signals yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
