import React, { useEffect, useState } from "react";
import { getLive, getHourlyHistory } from "../services/pumpxApi";
import { Line } from "react-chartjs-2";
import "chart.js/auto";

export default function PumpxHourlyChartTab() {
    const [token, setToken] = useState("");
    const [rows, setRows] = useState([]);
    const [error, setError] = useState(null);

    async function loadHistory(mint) {
        const data = await getHourlyHistory(mint);
        if (!data) {
            setError("No history available.");
            setRows([]);
            return;
        }
        setError(null);
        setRows(data);
    }

    async function pickToken() {
        const live = await getLive();
        if (!live) return;

        const t = live[0]; // highest ML token
        if (t) {
            setToken(t.mint);
            loadHistory(t.mint);
        }
    }

    useEffect(() => {
        pickToken();
    }, []);

    const chart = {
        labels: rows.map((r) => new Date(r.timestamp).toLocaleTimeString()),
        datasets: [
            {
                label: "Price (USD)",
                data: rows.map((r) => r.price),
                borderColor: "#6f9dff",
                backgroundColor: "rgba(111,157,255,0.3)",
                tension: 0.3,
            },
        ],
    };

    return (
        <div className="panel">
            <h2>PumpX Hourly Chart (OHLC)</h2>

            {token && <p>Tracking: {token}</p>}
            {error && <p style={{ color: "red" }}>{error}</p>}

            {rows.length > 0 ? (
                <Line data={chart} height={80} />
            ) : (
                <p>No chart data yet.</p>
            )}
        </div>
    );
}
