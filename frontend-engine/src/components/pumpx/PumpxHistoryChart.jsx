import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function PumpxHistoryChart({ history }) {
  if (!history.length) return <div>No history available</div>;

  return (
    <div style={{ height: 250 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={history}>
          <XAxis dataKey="timestamp" hide />
          <YAxis yAxisId="left" tickFormatter={(v) => v.toExponential(2)} />
          <YAxis
            yAxisId="right"
            orientation="right"
            domain={[0, 1]}
            tickFormatter={(v) => Math.round(v * 100) + "%"}
          />
          <Tooltip />
          <Line
            yAxisId="left"
            dataKey="price"
            stroke="#22ccff"
            dot={false}
            strokeWidth={1}
          />
          <Line
            yAxisId="right"
            dataKey="pump_probability"
            stroke="#ff00aa"
            dot={false}
            strokeDasharray="4 2"
            strokeWidth={1}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
