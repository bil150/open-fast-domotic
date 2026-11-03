import {
  ButtonAction,
  EffectName,
  ButtonMapping,
  CoordinatorStatus,
  Device,
  LightRequest,
  LightsOrder,
  Scene,
  SceneInput,
  Schedule,
  ScheduleInput,
  Sequence,
  SequenceInput,
  Zone,
  ZoneInput,
} from "./types";

// Empty by default: the API is on the same origin (the server serves the client; nginx and the Vite proxy forward /api).
// Set VITE_API_URL in the .env to call an API elsewhere.
const ORIGIN = import.meta.env.VITE_API_URL ?? "";
export const API_BASE = `${ORIGIN}/api/v1`;

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** FastAPI answers {detail: "text"} or {detail: [{loc, msg}, ...]} for validation errors. */
export function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).slice(1).join(".")} ${d.msg ?? ""}`.trim())
      .join(", ");
  }
  return fallback;
}

async function send(path: string, init: RequestInit): Promise<Response> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      /* not JSON */
    }
    throw new ApiError(response.status, errorMessage(body, response.statusText));
  }
  return response;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  return (await send(path, init)).json() as Promise<T>;
}

/** For the 204 answers (DELETE). */
async function requestNoContent(path: string, init: RequestInit): Promise<void> {
  await send(path, init);
}

const json = (method: string, body?: unknown): RequestInit =>
  body === undefined ? { method } : { method, body: JSON.stringify(body) };

const enc = encodeURIComponent;

/** Rooms and groups share the same CRUD. */
const zones = (path: "/rooms" | "/groups") => ({
  list: () => request<Zone[]>(path),
  create: (zone: ZoneInput) => request<Zone>(path, json("POST", zone)),
  update: (id: number, zone: ZoneInput) => request<Zone>(`${path}/${id}`, json("PUT", zone)),
  remove: (id: number) => requestNoContent(`${path}/${id}`, json("DELETE")),
  /** Switch the lights of the zone on or off, brighter or dimmer. Maps device id -> did it answer. */
  light: async (id: number, order: LightsOrder): Promise<Record<string, boolean>> =>
    (await request<{ results: Record<string, boolean> }>(`${path}/${id}/light`, json("PATCH", order))).results,
});

export const api = {
  /** Every light and socket of the home at once. */
  lights: async (order: LightsOrder): Promise<Record<string, boolean>> =>
    (await request<{ results: Record<string, boolean> }>("/lights", json("PATCH", order))).results,
  rooms: zones("/rooms"),
  groups: zones("/groups"),
  coordinator: {
    status: async (): Promise<CoordinatorStatus[]> =>
      (await request<{ coordinators: CoordinatorStatus[] }>("/coordinator")).coordinators,
    discover: (seconds = 60) =>
      request<{ info: string }>(`/coordinator/discovery?seconds=${seconds}`, json("POST")),
  },
  devices: {
    list: async (): Promise<Device[]> => (await request<{ devices: Device[] }>("/devices")).devices,
    /** Off the network, and forgotten by the server (rooms, groups, scenes, buttons...). */
    remove: (id: string) => requestNoContent(`/devices/${enc(id)}`, json("DELETE")),
    rename: (id: string, name: string | null) =>
      request<Device>(`/devices/${enc(id)}`, json("PATCH", { name })),
    light: (id: string, body: LightRequest) =>
      request<Device>(`/devices/${enc(id)}/light`, json("PATCH", body)),
    toggle: (id: string) => request<Device>(`/devices/${enc(id)}/toggle`, json("POST")),
    refresh: (id: string) => request<Device>(`/devices/${enc(id)}/refresh`, json("POST")),
    effect: async (id: string): Promise<EffectName | null> =>
      (await request<{ effect: EffectName | null }>(`/devices/${enc(id)}/effect`)).effect,
    startEffect: (id: string, effect: EffectName, brightness = 255) =>
      request<{ effect: EffectName }>(`/devices/${enc(id)}/effect`, json("PUT", { effect, brightness })),
    stopEffect: (id: string) => request<{ info: string }>(`/devices/${enc(id)}/animation`, json("DELETE")),
  },
  scenes: {
    list: () => request<Scene[]>("/scenes"),
    create: (scene: SceneInput) => request<Scene>("/scenes", json("POST", scene)),
    update: (id: number, scene: SceneInput) => request<Scene>(`/scenes/${id}`, json("PUT", scene)),
    remove: (id: number) => requestNoContent(`/scenes/${id}`, json("DELETE")),
    apply: async (id: number): Promise<Record<string, boolean>> =>
      (await request<{ results: Record<string, boolean> }>(`/scenes/${id}/apply`, json("POST"))).results,
    stop: (id: number) => request<{ info: string }>(`/scenes/${id}/stop`, json("POST")),
  },
  schedules: {
    list: () => request<Schedule[]>("/schedules"),
    create: (schedule: ScheduleInput) => request<Schedule>("/schedules", json("POST", schedule)),
    update: (id: number, schedule: ScheduleInput) =>
      request<Schedule>(`/schedules/${id}`, json("PUT", schedule)),
    remove: (id: number) => requestNoContent(`/schedules/${id}`, json("DELETE")),
  },
  sequences: {
    list: () => request<Sequence[]>("/sequences"),
    create: (sequence: SequenceInput) => request<Sequence>("/sequences", json("POST", sequence)),
    update: (id: number, sequence: SequenceInput) =>
      request<Sequence>(`/sequences/${id}`, json("PUT", sequence)),
    remove: (id: number) => requestNoContent(`/sequences/${id}`, json("DELETE")),
  },
  buttons: {
    list: (deviceId?: string) =>
      request<ButtonMapping[]>(`/buttons${deviceId ? `?device_id=${enc(deviceId)}` : ""}`),
    set: (deviceId: string, event: string, action: ButtonAction) =>
      request<ButtonMapping>("/buttons", json("PUT", { device_id: deviceId, event, action })),
    remove: (id: number) => requestNoContent(`/buttons/${id}`, json("DELETE")),
  },
};

export function liveUrl(): string {
  if (ORIGIN) return `${ORIGIN.replace(/^http/, "ws")}/api/v1/ws`;
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${window.location.host}/api/v1/ws`;
}

/** WebSocket for live effects: send {device_id, brightness?, hex_color?} as often as needed. */
export function streamUrl(): string {
  return liveUrl().replace(/\/ws$/, "/stream");
}
