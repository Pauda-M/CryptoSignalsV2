import React, { useEffect, useRef } from "react";
import { createChart } from "lightweight-charts";

function PriceChart({ symbol, timeframe, signals }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 320,
      layout: { background: { color: "#020617" }, textColor: "#e5e7eb" },
      grid: {
        vertLines: { visible: false },
        horzLines: { visible: false }
      },
      timeScale: { borderVisible: false },
      rightPriceScale: { borderVisible: false }
    });

    const candleSeries = chart.addCandlestickSeries();
    chartRef.current = chart;
    seriesRef.current = candleSeries;

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current) return;
    const load = async () => {
      const params = new URLSearchParams({
        symbol: symbol || "BTCUSDT",
        interval: timeframe || "15m",
        limit: "200"
      });
      const res = await fetch(`/api/market/klines?${params.toString()}`);
      const data = await res.json();
      const candles = data.candles.map((c) => ({
        time: Math.floor(c.time / 1000),
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close
      }));
      seriesRef.current.setData(candles);

      const markers = (signals || []).slice(0, 50).map((s) => ({
        time: Math.floor(new Date(s.created_at).getTime() / 1000),
        position: s.direction === "BUY" ? "belowBar" : "aboveBar",
        color:
          s.direction === "BUY"
            ? "#22c55e"
            : s.direction === "SELL"
            ? "#f97373"
            : "#e5e7eb",
        shape:
          s.direction === "BUY"
            ? "arrowUp"
            : s.direction === "SELL"
            ? "arrowDown"
            : "circle",
        text: `${s.direction} ${(s.confidence * 100).toFixed(0)}%`
      }));
      seriesRef.current.setMarkers(markers);
    };
    load();
  }, [symbol, timeframe, signals]);

  return (
    <div className="chart-card">
      <h2>
        {symbol} – {timeframe}
      </h2>
      <div ref={containerRef} style={{ width: "100%", height: "320px" }} />
    </div>
  );
}

export default PriceChart;
