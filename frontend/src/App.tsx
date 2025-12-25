import { useEffect, useMemo, useRef, useState } from "react";
import { useFloorcast } from "./hooks/useFloorcast";
import type { Entity } from "./types";
import "./App.css";

function App() {
  const { registry, entityStates, connected } = useFloorcast();
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
    console.log("selectedFloorId", selectedFloorId);
    console.log("registry", registry.areas);

    // Get areas on this floor
    const areasOnFloor = Object.values(registry.areas).filter(
      (a) => a.floor_id === selectedFloorId
    );
    console.log("areasOnFloor", areasOnFloor);
    const areaIds = new Set(areasOnFloor.map((a) => a.id));
    console.log("areaIds", areaIds);
    console.log("entities", registry.entities);

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
