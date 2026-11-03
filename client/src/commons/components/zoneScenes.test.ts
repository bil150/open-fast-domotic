import { expect, test } from "vitest";
import { Device } from "../../api/types";
import { assignmentsAfterRemoval, colorFromSwatch, cssColor, swatchFromColor, takesColors, without } from "./CZoneSceneEditor";

const device = (capabilities: string[]): Device => ({
  id: "d",
  protocol: "z",
  name: "D",
  model: "M",
  manufacturer: "ACME",
  type: "BULB",
  capabilities,
  online: true,
  last_seen: null,
  state: {},
});

test("a color keeps its kind and brightness through the editor", () => {
  const color = colorFromSwatch(swatchFromColor({ hex_color: "#ff0000", brightness: 127 }));
  expect(color.hex_color).toBe("#ff0000");
  expect(color.color_temp_kelvin).toBeUndefined();
  expect(color.brightness).toBeGreaterThan(120);
  expect(color.brightness).toBeLessThan(135);

  const white = colorFromSwatch(swatchFromColor({ color_temp_kelvin: 2700 }));
  expect(white.color_temp_kelvin).toBe(2700);
  expect(white.hex_color).toBeUndefined();
});

test("a white is previewed with a color", () => {
  expect(cssColor({ hex_color: "#00ff00" })).toBe("#00ff00");
  expect(cssColor({ color_temp_kelvin: 2700 })).toMatch(/^#[0-9a-f]{6}$/);
});

test("removing a color drops the lights placed on it and shifts the following ones", () => {
  expect(assignmentsAfterRemoval({ a: 0, b: 1, c: 2 }, 1)).toEqual({ a: 0, c: 1 });
});

test("a socket takes no color, a bulb does", () => {
  expect(takesColors(device(["on_off"]))).toBe(false);
  expect(takesColors(device(["on_off", "brightness"]))).toBe(true);
  expect(takesColors(device(["on_off", "color_temp"]))).toBe(true);
});

test("without drops one device and keeps the others", () => {
  expect(without({ a: true, b: false }, "a")).toEqual({ b: false });
});
