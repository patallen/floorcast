import { useEffect, useMemo, useRef, useState } from "react";
import { useFloorcast } from "./hooks/useFloorcast";
import type { Entity, Registry, TimelineEvent } from "./types";
import "./App.css";

function App() {
  const { registry, entityStates, connected, timelineEvents } = useFloorcast();
  const [selectedFloorId, setSelectedFloorId] = useState<string | null>(null);
  const [changedEntities, setChangedEntities] = useState<Set<string>>(new Set());
  const prevStatesRef = useRef<Record<string, string | null>>({});

  // Track state changes and trigger flash effect
  useEffect(() => {
    const prevStates = prevStatesRef.current;
    const newlyChanged: string[] = [];

    for (const [entityId, state] of Object.entries(entityStates)) {
      if (prevStates[entityId] !== undefined && prevStates[entityId] !== state) {
        newlyChanged.push(entityId);
      }
    }

    if (newlyChanged.length > 0) {
      setChangedEntities((prev) => new Set([...prev, ...newlyChanged]));

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
  }, [entityStates]);

  const floors = useMemo(() => {
    if (!registry) return [];
    return Object.values(registry.floors).sort(
      (a, b) => (a.level ?? 0) - (b.level ?? 0)
    );
  }, [registry]);

  const entitiesOnFloor = useMemo(() => {
    if (!registry || !selectedFloorId) return [];
    // Get areas on this floor
    const areasOnFloor = Object.values(registry.areas).filter(
      (a) => a.floor_id === selectedFloorId
    );
    const areaIds = new Set(areasOnFloor.map((a) => a.id));

    // Get entities in those areas (direct or via device) that have state
    return Object.values(registry.entities).filter((e) => {
      if (entityStates[e.id] === undefined) return false;
      const entityArea = e.area_id;
      const deviceArea = e.device_id ? registry.devices[e.device_id]?.area_id : null;
      const effectiveArea = entityArea ?? deviceArea;
      return effectiveArea && areaIds.has(effectiveArea);
    });
  }, [registry, selectedFloorId, entityStates]);

  // Auto-select first floor
  useEffect(() => {
    if (floors.length > 0 && !selectedFloorId) {
      setSelectedFloorId(floors[0].id); // eslint-disable-line
    }
  }, [floors, selectedFloorId]);

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
        <span className="connection-status">● Connected</span>
      </header>

      <nav className="floor-tabs">
        {floors.map((floor) => (
          <button
            key={floor.id}
            className={selectedFloorId === floor.id ? "active" : ""}
            onClick={() => setSelectedFloorId(floor.id)}
          >
            {floor.display_name}
          </button>
        ))}
      </nav>

      <main>
        {entitiesOnFloor.length === 0 ? (
          <p className="empty">No entities on this floor</p>
        ) : (
          <div className="entity-grid">
            {entitiesOnFloor.map((entity) => (
              <EntityCard
                key={entity.id}
                entity={entity}
                state={entityStates[entity.id]}
                deviceName={entity.device_id ? registry.devices[entity.device_id]?.display_name : undefined}
                areaName={
                  registry.areas[entity.area_id ?? registry.devices[entity.device_id ?? ""]?.area_id ?? ""]?.display_name
                }
                changed={changedEntities.has(entity.id)}
              />
            ))}
          </div>
        )}
      </main>

      <Timeline events={timelineEvents} registry={registry} />
    </div>
  );
}

const TIME_SCALES = [
  { label: "1m", ms: 60 * 1000 },
  { label: "5m", ms: 5 * 60 * 1000 },
  { label: "15m", ms: 15 * 60 * 1000 },
  { label: "1h", ms: 60 * 60 * 1000 },
];

function Timeline({ events, registry }: { events: TimelineEvent[]; registry: Registry | null }) {
  const [now, setNow] = useState(Date.now());
  const [timeWindow, setTimeWindow] = useState(5 * 60 * 1000);
  const windowStart = now - timeWindow;

  // Use requestAnimationFrame for smooth updates
  useEffect(() => {
    let animationId: number;
    const tick = () => {
      setNow(Date.now());
      animationId = requestAnimationFrame(tick);
    };
    animationId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationId);
  }, []);

  const recentEvents = events.filter((e) => e.timestamp >= windowStart);

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
      <div className="timeline-track">
        {recentEvents.map((event, i) => {
          const position = ((event.timestamp - windowStart) / timeWindow) * 100;
          const entityName = registry?.entities[event.entity_id]?.display_name ?? event.entity_id;
          return (
            <div
              key={`${event.entity_id}-${event.timestamp}-${i}`}
              className="timeline-event"
              style={{ transform: `translateX(${position}cqw) translateX(-50%)` }}
              title={`${entityName}: ${event.state}`}
            />
          );
        })}
        <div className="timeline-now" />
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
}: {
  entity: Entity;
  state: string | null | undefined;
  deviceName?: string;
  areaName?: string;
  changed?: boolean;
}) {
  return (
    <div className={`entity-card ${state === "on" ? "on" : ""} ${changed ? "changed" : ""}`}>
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
