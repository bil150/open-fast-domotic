import { expect, test } from "vitest";
import { brightnessToPercent, hexToRgb, kelvinToRgb, percentToBrightness, rgbToHex } from "./color";

test("rgb <-> hex", () => {
  expect(rgbToHex({ red: 255, green: 136, blue: 0 })).toBe("#ff8800");
  expect(hexToRgb("#ff8800")).toEqual({ red: 255, green: 136, blue: 0 });
  expect(hexToRgb("nonsense")).toEqual({ red: 255, green: 255, blue: 255 });
});

test("rgbToHex clamps out of range values", () => {
  expect(rgbToHex({ red: 300, green: -5, blue: 0 })).toBe("#ff0000");
});

test("brightness conversion never exceeds 254 (255 is invalid in ZCL)", () => {
  expect(percentToBrightness(100)).toBe(254);
  expect(percentToBrightness(0)).toBe(0);
  expect(percentToBrightness(150)).toBe(254);
  expect(brightnessToPercent(254)).toBe(100);
  expect(brightnessToPercent(255)).toBe(100);
  expect(brightnessToPercent(127)).toBe(50);
  expect(brightnessToPercent(null)).toBe(100);
});

test("warm white is more red than blue, cold white the opposite", () => {
  const warm = kelvinToRgb(2200);
  const cold = kelvinToRgb(6500);
  expect(warm.red).toBeGreaterThan(warm.blue);
  expect(cold.blue).toBeGreaterThanOrEqual(cold.red - 10);
});
