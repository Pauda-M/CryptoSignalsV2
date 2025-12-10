import { useEffect } from "react";
import { io } from "socket.io-client";
import { usePumpxStore } from "../store/pumpxStore";

// IMPORTANT:
// This MUST match the running pumpx-streamer port from server.js
const STREAMER_URL = "http://localhost:4101";

let socket = null;

export function usePumpxStream() {
  const setTokens = usePumpxStore((s) => s.setTokens);

  useEffect(() => {
    if (!socket) {
      socket = io(STREAMER_URL, {
        transports: ["websocket"],
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1500,
      });
    }

    socket.on("connect", () => {
      console.log("[PumpX] Connected:", socket.id);
    });

    socket.on("disconnect", () => {
      console.log("[PumpX] Disconnected");
    });

    socket.on("pumpx_snapshot", (rows) => {
      console.log("[PumpX] Snapshot:", rows.length, "tokens");
      setTokens(rows);
    });

    return () => {
      // do NOT disconnect globally (we want singleton socket)
    };
  }, []);
}
