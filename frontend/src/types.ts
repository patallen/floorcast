export interface Entity {
  id: string;
  entity_category: string;
  domain: string;
  display_name: string;
  device_id: string | null;
  area_id: string | null;
}

export interface Device {
  id: string;
  area_id: string | null;
  display_name: string;
}

export interface Area {
  id: string;
  display_name: string;
  floor_id: string | null;
}

export interface Floor {
  id: string;
  display_name: string;
  level: number | null;
}

export interface Registry {
  entities: Record<string, Entity>;
  devices: Record<string, Device>;
  areas: Record<string, Area>;
  floors: Record<string, Floor>;
}

export interface EntityStateValue {
  value: string | null;
  unit: string | null;
}

export interface EntityState {
  [entityId: string]: EntityStateValue;
}

export type WSMessage =
  | { type: "registry"; registry: Registry }
  | { type: "connected"; subscriber_id: string }
  | { type: "snapshot"; state: EntityState }
  | { type: "event"; entity_id: string; state: string | null; unit: string | null; timestamp: number; id: number };

export interface TimelineEvent {
  entity_id: string;
  state: string | null;
  unit: string | null;
  timestamp: number;
  id: number;
}
