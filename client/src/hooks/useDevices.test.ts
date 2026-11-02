import { expect, test } from "vitest";
import { Device, LiveMessage } from "../api/types";
import { applyLiveMessage } from "./useDevices";

const device = (id: string, overrides: Partial<Device> = {}): Device => ({
  id,
  protocol: "zigbee",
  name: id,
  model: "m",
  manufacturer: "x",
  type: "BULB",
  capabilities: ["on_off"],
  online: null,
  last_seen: null,
  state: {},
  ...overrides,
});

test("a state message updates only the matching device", () => {
  const message: LiveMessage = { type: "state", device_id: "a", data: { state: { power: true }, online: true } };
  const [a, b] = applyLiveMessage([device("a"), device("b")], message);
  expect(a?.state.power).toBe(true);
  expect(a?.online).toBe(true);
  expect(b?.state.power).toBeUndefined();
});

test("a state message keeps the fields it does not mention", () => {
  const start = [device("a", { state: { brightness: 100, temperature: 20 }, online: true })];
  const [a] = applyLiveMessage(start, { type: "state", device_id: "a", data: { state: { temperature: 21 } } });
  expect(a?.state).toEqual({ brightness: 100, temperature: 21 });
  expect(a?.online).toBe(true); // no `online` in the message: unchanged
});

test("a button message records the last press", () => {
  const [a] = applyLiveMessage([device("a")], {
    type: "button",
    device_id: "a",
    data: { event: "on_off.toggle", at: "2026-01-01T10:00:00" },
  });
  expect(a?.state.last_button).toEqual({ event: "on_off.toggle", at: "2026-01-01T10:00:00" });
  expect(a?.online).toBe(true);
});

test("joined/left messages leave the list untouched (the hook reloads it)", () => {
  const list = [device("a")];
  expect(applyLiveMessage(list, { type: "joined", device_id: "z", data: {} })).toBe(list);
});
