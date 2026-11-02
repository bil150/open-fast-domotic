import { expect, test } from "vitest";
import { Device } from "../../api/types";
import { anyOn, averageBrightness } from "./CLightsControls";

const device = (capabilities: string[], state: Device["state"]): Device => ({
  id: "d",
  protocol: "zigbee",
  name: "D",
  model: "M",
  manufacturer: "ACME",
  type: "BULB",
  capabilities,
  online: true,
  last_seen: null,
  state,
});

const bulb = (state: Device["state"]) => device(["on_off", "brightness"], state);
const socket = (state: Device["state"]) => device(["on_off"], state);

test("the button switches everything off as soon as one light or socket is on", () => {
  expect(anyOn([bulb({ power: false }), socket({ power: true })])).toBe(true);
  expect(anyOn([bulb({ power: false }), socket({ power: false })])).toBe(false);
  expect(anyOn([])).toBe(false);
});

test("the slider shows the average of the lights that are on, sockets and sensors left out", () => {
  const sensor = device(["temperature"], { power: true });
  const lights = [bulb({ power: true, brightness: 254 }), bulb({ power: true, brightness: 127 }), bulb({ power: false, brightness: 10 })];
  expect(averageBrightness([...lights, socket({ power: true }), sensor])).toBe(75);
});

test("when everything is off the slider shows the average level the lights would come on at", () => {
  expect(averageBrightness([bulb({ power: false, brightness: 127 }), bulb({ power: false, brightness: 127 })])).toBe(50);
  expect(averageBrightness([socket({ power: true })])).toBe(100);
});
