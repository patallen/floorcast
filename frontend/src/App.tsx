import { useEffect, useMemo, useRef, useState } from "react";
import { useFloorcast } from "./hooks/useFloorcast";
import type { Entity, TimelineEvent } from "./types";
import "./App.css";

function App() {
  const { registry, entityStates, connected, timelineEvents, fetchTimeline } = useFloorcast();
  const [changedEntities, setChangedEntities] = useState<Set<string>>(new Set());
  const prevStatesRef = useRef<Record<string, string | null>>({});
  const [playhead, setPlayhead] = useState<number | null>(null); // null = live
  const [hoveredEntity, setHoveredEntity] = useState<string | null>(null);
  const [groupBy, setGroupBy] = useState<"floor" | "area" | "device">("floor");
  const [viewMode, setViewMode] = useState<"all" | "tabs">("all");
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);

  // Pre-index events by entity for fast lookups
  const eventsByEntity = useMemo(() => {
    const index: Record<string, TimelineEvent[]> = {};
    for (const event of timelineEvents) {
      if (!index[event.entity_id]) index[event.entity_id] = [];
      index[event.entity_id].push(event);
    }
    return index;
  }, [timelineEvents]);

  // Compute state at playhead time (optimized with per-entity binary search)
  const effectiveStates = useMemo(() => {
    if (playhead === null) return entityStates;

    // Binary search to find the last event at or before playhead
    const findLastBefore = (arr: TimelineEvent[], target: number): TimelineEvent | null => {
      let left = 0;
      let right = arr.length - 1;
      let result: TimelineEvent | null = null;
      while (left <= right) {
        const mid = Math.floor((left + right) / 2);
        if (arr[mid].timestamp <= target) {
          result = arr[mid];
          left = mid + 1;
        } else {
          right = mid - 1;
        }
      }
      return result;
    };

    // For each entity with events, find state at playhead
    const stateAtTime: Record<string, string | null> = {};
    for (const [entityId, events] of Object.entries(eventsByEntity)) {
      const lastEvent = findLastBefore(events, playhead);
      if (lastEvent) {
        stateAtTime[entityId] = lastEvent.state;
      }
    }

    return { ...entityStates, ...stateAtTime };
  }, [playhead, entityStates, eventsByEntity]);

  // Track state changes and trigger flash effect (only when live)
  useEffect(() => {
    // Don't flash when scrubbing/playing back
    if (playhead !== null) {
      prevStatesRef.current = { ...entityStates };
      return;
    }

    const prevStates = prevStatesRef.current;
    const newlyChanged: string[] = [];

    for (const [entityId, state] of Object.entries(entityStates)) {
      if (prevStates[entityId] !== undefined && prevStates[entityId] !== state) {
        newlyChanged.push(entityId);
      }
    }

    if (newlyChanged.length > 0) {
      queueMicrotask(() => {
        setChangedEntities((prev) => new Set([...prev, ...newlyChanged]));
      });

      // Remove flash after animation completes
      setTimeout(() => {
        setChangedEntities((prev) => {
          const next = new Set(prev);
          newlyChanged.forEach((id) => next.delete(id));
          return next;
        });
      }, 1000);
    }

    prevStatesRef.current = { ...entityStates };
  }, [entityStates, playhead]);

  // Get all entities with state
  const entitiesWithState = useMemo(() => {
    if (!registry) return [];
    return Object.values(registry.entities).filter(
      (e) => effectiveStates[e.id] !== undefined
    );
  }, [registry, effectiveStates]);

  // Compute groups based on groupBy mode
  const groups = useMemo(() => {
    if (!registry) return [];

    if (groupBy === "floor") {
      return Object.values(registry.floors)
        .sort((a, b) => (a.level ?? 0) - (b.level ?? 0))
        .map((floor) => {
          const areasOnFloor = Object.values(registry.areas).filter(
            (a) => a.floor_id === floor.id
          );
          const areaIds = new Set(areasOnFloor.map((a) => a.id));
          const entities = entitiesWithState.filter((e) => {
            const entityArea = e.area_id;
            const deviceArea = e.device_id ? registry.devices[e.device_id]?.area_id : null;
            const area = entityArea ?? deviceArea;
            return area && areaIds.has(area);
          });
          return { id: floor.id, name: floor.display_name, entities };
        })
        .filter((g) => g.entities.length > 0);
    }

    if (groupBy === "area") {
      return Object.values(registry.areas)
        .sort((a, b) => a.display_name.localeCompare(b.display_name))
        .map((area) => {
          const entities = entitiesWithState.filter((e) => {
            const entityArea = e.area_id;
            const deviceArea = e.device_id ? registry.devices[e.device_id]?.area_id : null;
            return (entityArea ?? deviceArea) === area.id;
          });
          return { id: area.id, name: area.display_name, entities };
        })
        .filter((g) => g.entities.length > 0);
    }

    if (groupBy === "device") {
      const deviceGroups = Object.values(registry.devices)
        .sort((a, b) => a.display_name.localeCompare(b.display_name))
        .map((device) => {
          const entities = entitiesWithState.filter((e) => e.device_id === device.id);
          return { id: device.id, name: device.display_name, entities };
        })
        .filter((g) => g.entities.length > 0);

      // Also add entities without a device
      const noDeviceEntities = entitiesWithState.filter((e) => !e.device_id);
      if (noDeviceEntities.length > 0) {
        deviceGroups.push({ id: "_no_device", name: "No Device", entities: noDeviceEntities });
      }
      return deviceGroups;
    }

    return [];
  }, [registry, groupBy, entitiesWithState]);

  // Auto-select first group when switching to tabs mode or when groups change
  useEffect(() => {
    if (viewMode === "tabs" && groups.length > 0) {
      if (!selectedGroupId || !groups.find((g) => g.id === selectedGroupId)) {
        queueMicrotask(() => setSelectedGroupId(groups[0].id));
      }
    }
  }, [viewMode, groups, selectedGroupId]);

  const visibleGroups = viewMode === "all" ? groups : groups.filter((g) => g.id === selectedGroupId);

  if (!connected) {
    return <div className="status">Connecting...</div>;
  }

  if (!registry) {
    return <div className="status">Loading registry...</div>;
  }

  return (
    <div className="app">
      <header>
        <h1>Floorcast</h1>
        <div className="header-controls">
          <div className="group-by">
            <span>Group by:</span>
            {(["floor", "area", "device"] as const).map((mode) => (
              <button
                key={mode}
                className={groupBy === mode ? "active" : ""}
                onClick={() => setGroupBy(mode)}
              >
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </button>
            ))}
          </div>
          <div className="view-mode">
            <button
              className={viewMode === "all" ? "active" : ""}
              onClick={() => setViewMode("all")}
              title="Show all groups on one page"
            >
              All
            </button>
            <button
              className={viewMode === "tabs" ? "active" : ""}
              onClick={() => setViewMode("tabs")}
              title="Show one group at a time"
            >
              Tabs
            </button>
          </div>
          <span className="connection-status">● Connected</span>
        </div>
      </header>

      {viewMode === "tabs" && groups.length > 0 && (
        <nav className="group-tabs">
          {groups.map((group) => (
            <button
              key={group.id}
              className={selectedGroupId === group.id ? "active" : ""}
              onClick={() => setSelectedGroupId(group.id)}
            >
              {group.name}
            </button>
          ))}
        </nav>
      )}

      <main>
        {visibleGroups.length === 0 ? (
          <p className="empty">No entities found</p>
        ) : (
          visibleGroups.map((group) => (
            <section key={group.id} className="entity-group">
              <h2 className="group-title">{group.name}</h2>
              <div className="entity-grid">
                {group.entities.map((entity) => (
                  <EntityCard
                    key={entity.id}
                    entity={entity}
                    state={effectiveStates[entity.id]}
                    deviceName={groupBy !== "device" && entity.device_id ? registry.devices[entity.device_id]?.display_name : undefined}
                    areaName={
                      groupBy !== "area" ? registry.areas[entity.area_id ?? registry.devices[entity.device_id ?? ""]?.area_id ?? ""]?.display_name : undefined
                    }
                    changed={changedEntities.has(entity.id)}
                    onHover={setHoveredEntity}
                  />
                ))}
              </div>
            </section>
          ))
        )}
      </main>

      <Timeline events={timelineEvents} onPlayheadChange={setPlayhead} hoveredEntity={hoveredEntity} fetchTimeline={fetchTimeline} />
    </div>
  );
}

const TIME_SCALES = [
  { label: "1m", ms: 60 * 1000 },
  { label: "5m", ms: 5 * 60 * 1000 },
  { label: "15m", ms: 15 * 60 * 1000 },
  { label: "1h", ms: 60 * 60 * 1000 },
];

function Timeline({
  events,
  onPlayheadChange,
  hoveredEntity,
  fetchTimeline,
}: {
  events: TimelineEvent[];
  onPlayheadChange: (time: number | null) => void;
  hoveredEntity: string | null;
  fetchTimeline: (startTime: Date, endTime: Date) => Promise<void>;
}) {
  const [playhead, setPlayhead] = useState(() => Date.now());
  const [windowEnd, setWindowEnd] = useState(() => Date.now());
  const [timeWindow, setTimeWindow] = useState(5 * 60 * 1000);
  const [paused, setPaused] = useState(false);
  const [live, setLive] = useState(true);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  // eslint-disable-next-line react-hooks/purity
  const lastTickRef = useRef(Date.now());
  const windowStart = windowEnd - timeWindow;

  // Fetch historical data when time window scale changes or user scrubs back
  const lastFetchRef = useRef({ windowStart: 0, timeWindow: 0 });
  useEffect(() => {
    // Only fetch when timeWindow changes (user selected different scale) or window moves significantly
    const shouldFetch =
      timeWindow !== lastFetchRef.current.timeWindow ||
      windowStart < lastFetchRef.current.windowStart - 60000; // Moved back by more than 1 minute

    if (shouldFetch) {
      lastFetchRef.current = { windowStart, timeWindow };
      fetchTimeline(new Date(windowStart), new Date(windowEnd));
    }
  }, [windowStart, windowEnd, timeWindow, fetchTimeline]);

  // Use requestAnimationFrame for smooth updates
  const lastPlayheadUpdateRef = useRef(0);
  useEffect(() => {
    if (paused) return;
    let animationId: number;
    const tick = () => {
      const currentTime = Date.now();
      // Always keep window synced to real time so we see new events
      setWindowEnd(currentTime);

      if (live) {
        setPlayhead(currentTime);
      } else {
        // Advance playhead by elapsed time (playback mode) with speed multiplier
        const delta = (currentTime - lastTickRef.current) * playbackSpeed;
        setPlayhead((prev) => {
          const next = prev + delta;
          // Don't go past current time - switch to live if caught up
          if (next >= currentTime) {
            setLive(true);
            onPlayheadChange(null);
            return currentTime;
          }
          return next;
        });
        // Throttle playhead updates to parent (every 200ms)
        if (currentTime - lastPlayheadUpdateRef.current > 200) {
          lastPlayheadUpdateRef.current = currentTime;
          setPlayhead((prev) => {
            onPlayheadChange(prev);
            return prev;
          });
        }
      }
      lastTickRef.current = currentTime;
      animationId = requestAnimationFrame(tick);
    };
    lastTickRef.current = Date.now();
    animationId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationId);
  }, [paused, live, onPlayheadChange, playbackSpeed]);

  const goLive = () => {
    const now = Date.now();
    setPlayhead(now);
    setWindowEnd(now);
    setLive(true);
    setPaused(false);
    onPlayheadChange(null);
  };

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const scrubTo = (clientX: number) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const fraction = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    const timestamp = windowStart + fraction * timeWindow;
    setPlayhead(timestamp);
    setLive(false);
    onPlayheadChange(timestamp);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setPaused(true);
    scrubTo(e.clientX);

    const handleMouseMove = (e: MouseEvent) => scrubTo(e.clientX);
    const handleMouseUp = () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  };

  // Draw timeline on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const rect = container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, rect.width, rect.height);

    const labelHeight = 16;
    const trackTop = labelHeight + 2;

    // Draw events
    for (const event of events) {
      if (event.timestamp < windowStart || event.timestamp > windowEnd) continue;
      const x = ((event.timestamp - windowStart) / timeWindow) * rect.width;
      const isFaded = hoveredEntity !== null && hoveredEntity !== event.entity_id;
      ctx.strokeStyle = isFaded ? "rgba(45, 45, 72, 0.9)" : "rgba(100, 149, 237, 0.6)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, trackTop);
      ctx.lineTo(x, rect.height);
      ctx.stroke();
    }

    // Draw playhead
    const playheadX = ((playhead - windowStart) / timeWindow) * rect.width;
    const playheadColor = live ? "#4ade80" : "#a5b4fc";
    ctx.strokeStyle = playheadColor;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(playheadX, trackTop);
    ctx.lineTo(playheadX, rect.height);
    ctx.stroke();

    // Draw time label above playhead
    const timeStr = new Date(playhead).toLocaleTimeString("en-US", { hour12: false });
    ctx.font = "13px monospace";
    ctx.fillStyle = playheadColor;
    const textWidth = ctx.measureText(timeStr).width;
    let labelX = playheadX - textWidth / 2;
    // Keep label within bounds
    if (labelX < 2) labelX = 2;
    if (labelX + textWidth > rect.width - 2) labelX = rect.width - textWidth - 2;
    ctx.fillText(timeStr, labelX, 12);
  }, [events, windowStart, windowEnd, timeWindow, playhead, live, hoveredEntity]);

  const labelCount = 6;
  const labels = Array.from({ length: labelCount }, (_, i) => {
    const fraction = i / (labelCount - 1);
    const ms = timeWindow * (1 - fraction);
    if (ms === 0) return "now";
    if (ms >= 60 * 60 * 1000) return `-${Math.round(ms / (60 * 60 * 1000))}h`;
    if (ms >= 60 * 1000) return `-${Math.round(ms / (60 * 1000))}m`;
    return `-${Math.round(ms / 1000)}s`;
  });

  return (
    <div className="timeline">
      <div className="timeline-header">
        <div className="timeline-controls">
          <button
            className="timeline-play-pause"
            onClick={() => {
              if (!paused) setLive(false);
              setPaused(!paused);
            }}
            title={paused ? "Play" : "Pause"}
          >
            {paused ? "▶" : "⏸"}
          </button>
          <button
            className={`timeline-live ${live && !paused ? "active" : ""}`}
            onClick={goLive}
            title="Go to live"
          >
            LIVE
          </button>
          {!live && (
            <div className="timeline-speed">
              {[1, 2, 5, 10, 20].map((speed) => (
                <button
                  key={speed}
                  className={playbackSpeed === speed ? "active" : ""}
                  onClick={() => setPlaybackSpeed(speed)}
                >
                  {speed}x
                </button>
              ))}
            </div>
          )}
          <span className="timeline-time">
            {new Date(playhead).toLocaleTimeString()}
          </span>
        </div>
        <div className="timeline-scales">
          {TIME_SCALES.map((scale) => (
            <button
              key={scale.label}
              className={timeWindow === scale.ms ? "active" : ""}
              onClick={() => setTimeWindow(scale.ms)}
            >
              {scale.label}
            </button>
          ))}
        </div>
      </div>
      <div className="timeline-track" ref={containerRef} onMouseDown={handleMouseDown}>
        <canvas ref={canvasRef} className="timeline-canvas" />
      </div>
      <div className="timeline-labels">
        {labels.map((label, i) => (
          <span key={i}>{label}</span>
        ))}
      </div>
    </div>
  );
}

function formatState(state: string | null | undefined): string {
  if (state == null) return "unknown";
  const num = parseFloat(state);
  if (!isNaN(num)) {
    return num.toFixed(3).replace(/\.?0+$/, "");
  }
  return state;
}

function EntityCard({
  entity,
  state,
  deviceName,
  areaName,
  changed,
  onHover,
}: {
  entity: Entity;
  state: string | null | undefined;
  deviceName?: string;
  areaName?: string;
  changed?: boolean;
  onHover?: (entityId: string | null) => void;
}) {
  return (
    <div
      className={`entity-card ${state === "on" ? "on" : ""} ${changed ? "changed" : ""}`}
      onMouseEnter={() => onHover?.(entity.id)}
      onMouseLeave={() => onHover?.(null)}
    >
      <div className="entity-name">{entity.display_name}</div>
      {deviceName && <div className="entity-device">{deviceName}</div>}
      <div className="entity-state">{formatState(state)}</div>
      <div className="entity-meta">
        <span className="domain">{entity.domain}</span>
        {areaName && <span className="area">{areaName}</span>}
      </div>
    </div>
  );
}

export default App;
