import { ColorRGB } from "../types/ColorRGB";

export const MAX_BRIGHTNESS = 254; // 255 is not a valid ZCL level

/** Seconds a light takes to reach a color or brightness picked in the app: a glide, not a jump. */
export const UI_FADE_SECONDS = 1;

export function rgbToHex({ red, green, blue }: ColorRGB): string {
  const part = (v: number) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0");
  return `#${part(red)}${part(green)}${part(blue)}`;
}

export function hexToRgb(hex: string): ColorRGB {
  const clean = hex.replace("#", "");
  const value = /^[0-9a-fA-F]{6}$/.test(clean) ? clean : "ffffff";
  return {
    red: parseInt(value.slice(0, 2), 16),
    green: parseInt(value.slice(2, 4), 16),
    blue: parseInt(value.slice(4, 6), 16),
  };
}

export const brightnessToPercent = (brightness?: number | null): number =>
  brightness == null ? 100 : Math.round((Math.min(brightness, MAX_BRIGHTNESS) / MAX_BRIGHTNESS) * 100);

export const percentToBrightness = (percent: number): number =>
  Math.round((Math.max(0, Math.min(100, percent)) / 100) * MAX_BRIGHTNESS);

/** Rough on-screen color of a white light, for the preview pastille. */
export function kelvinToRgb(kelvin: number): ColorRGB {
  const t = Math.max(1000, Math.min(10000, kelvin)) / 100;
  const red = t <= 66 ? 255 : 329.698727446 * Math.pow(t - 60, -0.1332047592);
  const green =
    t <= 66 ? 99.4708025861 * Math.log(t) - 161.1195681661 : 288.1221695283 * Math.pow(t - 60, -0.0755148492);
  const blue = t >= 66 ? 255 : t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307;
  const clamp = (v: number) => Math.max(0, Math.min(255, Math.round(v)));
  return { red: clamp(red), green: clamp(green), blue: clamp(blue) };
}
