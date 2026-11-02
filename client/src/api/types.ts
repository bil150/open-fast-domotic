export type DeviceType =
  | "BULB"
  | "POWER_SOCKET"
  | "TEMPERATURE_SENSOR"
  | "BUTTON"
  | "UNKNOWN";

export interface ButtonEventState {
  event: string;
  at: string;
}

export interface DeviceState {
  power?: boolean | null;
  brightness?: number | null;
  hue?: number | null;
  saturation?: number | null;
  hex_color?: string | null;
  color_temp_kelvin?: number | null;
  temperature?: number | null;
  battery?: number | null;
  last_button?: ButtonEventState | null;
}

export interface Device {
  id: string;
  protocol: string;
  name: string;
  model: string;
  manufacturer: string;
  type: DeviceType;
  capabilities: string[];
  online: boolean | null;
  last_seen: string | null;
  state: DeviceState;
  color_temp_range_kelvin?: [number, number] | null;
}

/** FX available on bulbs (random flicker). */
export type EffectName = "fire" | "candle";

export interface LightRequest {
  power?: boolean;
  brightness?: number; // 0..255
  hue?: number;
  saturation?: number;
  hex_color?: string;
  color_temp_kelvin?: number;
  transition_time?: number;
}

export interface SceneAction extends LightRequest {
  device_id: string;
}

/** One color of a scene: a color or a white, with an optional brightness (0..255). */
export interface PaletteColor {
  hex_color?: string;
  color_temp_kelvin?: number;
  brightness?: number;
}

/** How long the lights take to glide to their color: 2 s, 6 s or 15 s. The only three, so it never stutters. */
export type Speed = "fast" | "medium" | "slow";

export const SPEED_SECONDS: Record<Speed, number> = { fast: 2, medium: 6, slow: 15 };

export interface SceneTarget {
  type: "room" | "group";
  id: number;
}

/**
 * Either `actions` (one state per device, older scenes) or `target` + `palette`:
 * the colors are spread over the lights of the room/group.
 */
export interface Scene {
  id: number;
  name: string;
  actions: SceneAction[];
  target?: SceneTarget | null;
  palette?: PaletteColor[];
  assignments?: Record<string, number>; // device id -> palette index
  switches?: Record<string, boolean>; // device id -> on/off: sockets, and lights that must be off
  speed?: Speed | null; // palette scenes: the glide to a color (and, animated, how long each color lasts)
  fade?: number; // seconds, what the speed stands for
  animated?: boolean; // the lights step through the palette in a loop
  duration?: number; // seconds each color lasts, animated
  running?: boolean; // animated: the loop is running
}

export interface SceneInput {
  name: string;
  actions?: SceneAction[];
  target?: SceneTarget;
  palette?: PaletteColor[];
  assignments?: Record<string, number>;
  switches?: Record<string, boolean>;
  speed?: Speed;
  animated?: boolean;
}

/** One order for many lights (a room, a group, the whole home). */
export interface LightsOrder {
  power?: boolean; // every light and socket
  brightness?: number; // 1..255, on the lights that dim
  brightness_step?: number; // percent to add (or remove, if negative) to each light
  transition_time?: number;
}

/** A room (a device is in one at most) or a group (a device can be in several). */
export interface Zone {
  id: number;
  name: string;
  device_ids: string[];
}

export interface ZoneInput {
  name: string;
  device_ids: string[];
}

export interface Schedule {
  id: number;
  name: string;
  cron: string;
  scene_id: number;
  enabled: boolean;
  last_run?: string | null;
  next_run?: string | null;
}

export interface ScheduleInput {
  name: string;
  cron: string;
  scene_id: number;
  enabled: boolean;
}

export interface SequenceStep {
  scene_id: number;
  duration: number; // seconds
  fade?: boolean; // glide to the scene during the whole duration (default true)
}

export interface Sequence {
  id: number;
  name: string;
  steps: SequenceStep[];
  loop: boolean;
  enabled: boolean;
  running: boolean;
}

export interface SequenceInput {
  name: string;
  steps: SequenceStep[];
  loop: boolean;
  enabled: boolean;
}

export type ButtonAction =
  | { type: "scene"; scene_id: number }
  | { type: "toggle"; device_id: string }
  | { type: "power"; device_id: string; state: boolean };

export interface ButtonMapping {
  id: number;
  device_id: string;
  event: string;
  action: ButtonAction;
}

export interface CoordinatorStatus {
  protocol: string;
  ready: boolean;
  last_error?: string | null;
  discovery_remaining?: number;
  devices?: number;
}

export interface LiveMessage {
  type: "state" | "button" | "joined" | "left";
  device_id: string;
  data: {
    state?: DeviceState;
    online?: boolean | null;
    event?: string;
    at?: string;
  };
}
