import { useCallback, useEffect, useRef, useState } from "react";
import type { EntityState, Registry, TimelineEvent, WSMessage } from "../types";

const WS_PROTOCOL = window.location.protocol === "https:" ? "wss:" : "ws:";
const WS_URL = `${WS_PROTOCOL}//${window.location.host}/events/live`;
const API_URL = `${window.location.protocol}//${window.location.host}`;
const MAX_TIMELINE_EVENTS = 10000;

export function useFloorcast() {
  const [registry, setRegistry] = useState<Registry | null>(null);
  const [entityStates, setEntityStates] = useState<EntityState>({});
  const [connected, setConnected] = useState(false);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [timelineRange, setTimelineRange] = useState<{ start: number; end: number } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fetchingRef = useRef(false);

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
          setTimelineEvents((prev) => {
            const newEvent: TimelineEvent = {
              entity_id: message.entity_id,
              state: message.state,
              timestamp: Date.now(),
            };
            const updated = [...prev, newEvent];
            return updated.slice(-MAX_TIMELINE_EVENTS);
          });
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

  // Fetch historical timeline data
  const fetchTimeline = useCallback(async (startTime: Date, endTime: Date) => {
    if (fetchingRef.current) return;

    // Check if we already have this range
    if (timelineRange) {
      const startMs = startTime.getTime();
      const endMs = endTime.getTime();
      if (startMs >= timelineRange.start && endMs <= timelineRange.end) {
        return; // Already have this data
      }
    }

    fetchingRef.current = true;
    try {
      const params = new URLSearchParams({
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString(),
      });
      const response = await fetch(`${API_URL}/timeline?${params}`);
      if (!response.ok) throw new Error("Failed to fetch timeline");

      const data = await response.json();

      // Convert backend events to TimelineEvent format
      const historicalEvents: TimelineEvent[] = data.events.map((e: { entity_id: string; state: string | null; timestamp: string }) => ({
        entity_id: e.entity_id,
        state: e.state,
        timestamp: new Date(e.timestamp).getTime(),
      }));

      setTimelineEvents((prev) => {
        // Merge historical events with existing, removing duplicates
        const existingTimestamps = new Set(prev.map((e) => `${e.entity_id}-${e.timestamp}`));
        const newEvents = historicalEvents.filter(
          (e) => !existingTimestamps.has(`${e.entity_id}-${e.timestamp}`)
        );
        const merged = [...newEvents, ...prev].sort((a, b) => a.timestamp - b.timestamp);
        return merged.slice(-MAX_TIMELINE_EVENTS);
      });

      setTimelineRange((prev) => {
        const startMs = startTime.getTime();
        const endMs = endTime.getTime();
        if (!prev) return { start: startMs, end: endMs };
        return {
          start: Math.min(prev.start, startMs),
          end: Math.max(prev.end, endMs),
        };
      });
    } catch (error) {
      console.error("Failed to fetch timeline:", error);
    } finally {
      fetchingRef.current = false;
    }
  }, [timelineRange]);

  return { registry, entityStates, connected, timelineEvents, fetchTimeline };
}
