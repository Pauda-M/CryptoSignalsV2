import React, { useEffect, useState } from "react";
import { getRadar } from "../services/pumpxApi";

export default function PumpxRadarTab() {
    const [rows, setRows] = useState([]);
    const [error, setError] = useState(null);
    const [filters, setFilters] = useState({
        ml: 0.2,
        mcap: 1000,
        buys1h: 2,
        change1h: 10,
    });

    async function load() {
        const data = await getRadar(filters);
        if (!data) {
            setError("Radar fetch failed.");
            setRows([]);
            return;
        }
        setError(null);
        setRows(data.rows || data);
    }

    useEffect(() => {
        load();
        const id = setInterval(load, 10000);
        return () => clearInterval(id);
    }, [filters]);

    return (
        <div className="panel">
            <h2>PumpX Radar</h2>

            {error && <p style={{ color: "red" }}>{error}</p>}

            <div className="filters">
                <label>
                    Min ML:
                    <input
                        type="number"
                        value={filters.ml}
                        step="0.1"
                        onChange={(e) => setFilters({ ...filters, ml: parseFloat(e.target.value) })}
                    />
                </label>

                <label>
                    Min MCAP:
                    <input
                        type="number"
                        value={filters.mcap}
                        onChange={(e) => setFilters({ ...filters, mcap: parseFloat(e.target.value) })}
                    />
                </label>

                <label>
                    Min buys 1h:
                    <input
                        type="number"
                        value={filters.buys1h}
                        onChange={(e) => setFilters({ ...filters, buys1h: parseInt(e.target.value) })}
                    />
                </label>

                <label>
                    Min Δ1h %:
                    <input
                        type="number"
                        value={filters.change1h}
                        onChange={(e) => setFilters({ ...filters, change1h: parseFloat(e.target.value) })}
                    />
                </label>
            </div>

            <table className="table">
                <thead>
                    <tr>
                        <th>Prob%</th>
                        <th>Token</th>
                        <th>MCAP</th>
                        <th>Price</th>
                        <th>Vol 5m</th>
                        <th>Buys 5m</th>
                        <th>Sells 5m</th>
                        <th>Buys 1h</th>
                        <th>Δ1h%</th>
                        <th>Age</th>
                        <th>Updated</th>
                    </tr>
                </thead>

                <tbody>
                    {rows.length === 0 && (
                        <tr>
                            <td colSpan="11">No tokens match current filters.</td>
                        </tr>
                    )}

                    {rows.map((r) => (
                        <tr key={r.token_id}>
                            <td>{(r.pump_probability * 100).toFixed(1)}%</td>
                            <td>{r.name}</td>
                            <td>{r.marketcap?.toFixed(0)}</td>
                            <td>{r.price}</td>
                            <td>{r.volume_5m?.toFixed(2)}</td>
                            <td>{r.buys_5m}</td>
                            <td>{r.sells_5m}</td>
                            <td>{r.buys_1h}</td>
                            <td>{(r.price_change_1h * 100)?.toFixed(2)}%</td>
                            <td>{Math.floor(r.age_seconds / 60)}m</td>
                            <td>{new Date(r.updated_at).toLocaleTimeString()}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
