import React, { useEffect, useState } from "react";
import { getAlerts } from "../services/pumpxApi";

export default function PumpxAlertsTab() {
    const [alerts, setAlerts] = useState([]);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);

    async function load() {
        setLoading(true);
        const data = await getAlerts();
        if (!data) {
            setError("Failed to load alerts");
            setLoading(false);
            return;
        }
        setAlerts(data);
        setError(null);
        setLoading(false);
    }

    useEffect(() => {
        load();
        const id = setInterval(load, 5000);
        return () => clearInterval(id);
    }, []);

    return (
        <div className="panel">
            <h2>PumpX Alerts</h2>

            {loading && <p>Loading alerts...</p>}
            {error && <p style={{ color: "red" }}>{error}</p>}

            <table className="table">
                <thead>
                    <tr>
                        <th>Signal</th>
                        <th>Token</th>
                        <th>Probability</th>
                        <th>Δ1h %</th>
                        <th>Updated</th>
                    </tr>
                </thead>

                <tbody>
                    {alerts.length === 0 && (
                        <tr>
                            <td colSpan="5">No active alerts</td>
                        </tr>
                    )}

                    {alerts.map((a, i) => (
                        <tr key={i}>
                            <td style={{ color: a.signal === "BUY" ? "lime" : "red" }}>
                                {a.signal}
                            </td>
                            <td>{a.name}</td>
                            <td>{(a.pump_probability * 100).toFixed(1)}%</td>
                            <td>{a.price_change_1h?.toFixed(2)}%</td>
                            <td>{new Date(a.updated_at).toLocaleTimeString()}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
