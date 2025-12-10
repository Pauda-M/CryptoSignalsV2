import { useEffect } from "react";
import { io } from "socket.io-client";

export function useSignalStream(onSignal) {
  useEffect(() => {
    const socket = io("http://localhost:4000", {
      transports: ["websocket"]
    });

    socket.on("connect", () => console.log("[WS] connected", socket.id));
    socket.on("signal", (sig) => {
      if (onSignal) onSignal(sig);
    });

    return () => {
      socket.disconnect();
    };
  }, [onSignal]);
}
