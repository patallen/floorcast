import { useEffect, useRef, useState } from "react";
import type { EntityState, Registry, WSMessage } from "../types";

const WS_URL = "ws://localhost:8000/events/live";

export function useFloorcast() {
  const [registry, setRegistry] = useState<Registry | null>(null);
  const [entityStates, setEntityStates] = useState<EntityState>({});
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onclose = () => {
      setConnected(false);
    };

    ws.onmessage = (event) => {
      const message: WSMessage = JSON.parse(event.data);

      switch (message.type) {
        case "registry":
          setRegistry(message.registry);
          break;
        case "snapshot":
          setEntityStates(message.state);
          break;
        case "event":
          setEntityStates((prev) => ({
            ...prev,
            [message.entity_id]: message.state,
          }));
          break;
        case "connected":
          console.log("Subscribed:", message.subscriber_id);
          break;
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  return { registry, entityStates, connected };
}
