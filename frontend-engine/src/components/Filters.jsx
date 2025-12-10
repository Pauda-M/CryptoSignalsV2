import React from "react";

function Filters({ asset, setAsset, timeframe, setTimeframe, onApply }) {
  const timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"];

  return (
    <div className="filters">
      <div className="filter-field">
        <label>Asset Symbol</label>
        <input
          type="text"
          placeholder="e.g. BTCUSDT"
          value={asset}
          onChange={(e) => setAsset(e.target.value.toUpperCase())}
        />
      </div>

      <div className="filter-field">
        <label>Timeframe</label>
        <div className="timeframe-radios">
          {timeframes.map((tf) => (
            <label key={tf}>
              <input
                type="radio"
                name="timeframe"
                value={tf}
                checked={timeframe === tf}
                onChange={(e) => setTimeframe(e.target.value)}
              />
              {tf}
            </label>
          ))}
        </div>
      </div>

      <button className="btn" onClick={onApply}>
        Apply
      </button>
    </div>
  );
}

export default Filters;
