import React, { useEffect, useState } from "react";
import { getLive } from "../services/pumpxApi";

export default function PumpxTrendsTab() {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);

    async function load() {
        setLoading(true);
        const data = await getLive();
        setLoading(false);

        if (!data) return;

        // Compute signal locally
        const processed = data.map((t) => ({
            ...t,
            signal: t.price_change_1h > 0.05 ? "BUY" : t.price_change_1h < -0.05 ? "SELL" : "",
        }));

        // Sort by ML prob
        processed.sort((a, b) => (b.pump_probability || 0) - (a.pump_probability || 0));

        setRows(processed);
    }

    useEffect(() => {
        load();
        const id = setInterval(load, 5000);
        return () => clearInterval(id);
    }, []);

    return (
        <div className="panel">
            <h2>PumpX Trends</h2>

            {loading && <p>Loading...</p>}

            <table className="table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Signal</th>
                        <th>Token</th>
                        <th>Mint</th>
                        <th>Score</th>
                        <th>ML%</th>
                        <th>Δ1h%</th>
                        <th>Buys-Sells (5m)</th>
                        <th>Vol 5m</th>
                    </tr>
                </thead>

                <tbody>
                    {rows.map((r, i) => (
                        <tr key={r.token_id}>
                            <td>{i + 1}</td>
                            <td style={{ color: r.signal === "BUY" ? "lime" : r.signal === "SELL" ? "red" : "white" }}>
                                {r.signal}
                            </td>
                            <td>{r.name}</td>
                            <td>{r.mint}</td>
                            <td>{r.score?.toFixed(1)}</td>
                            <td>{(r.pump_probability * 100).toFixed(1)}%</td>
                            <td>{(r.price_change_1h * 100)?.toFixed(2)}%</td>
                            <td>{r.buys_5m - r.sells_5m}</td>
                            <td>{r.volume_5m?.toFixed(1)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
