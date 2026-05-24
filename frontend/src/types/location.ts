export type PersistentLocationStatus =
  | "idle"
  | "requesting"
  | "active"
  | "denied"
  | "unavailable"
  | "error";

export type PersistentLocationSnapshot = {
  latitud: number;
  longitud: number;
  accuracy: number | null;
  timestamp: number;
};

export type PersistentLocationState = {
  status: PersistentLocationStatus;
  location: PersistentLocationSnapshot | null;
  stale: boolean;
  statusMessage: string | null;
  enabledForRole: boolean;
};
