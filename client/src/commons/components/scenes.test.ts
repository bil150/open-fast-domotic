import { expect, test } from "vitest";
import { Device, Sequence } from "../../api/types";
import { tileColor } from "./CDeviceBento";
import { actionFromRow, rowFromAction } from "./CSceneEditor";
import { describeSteps } from "./CSequencesPanel";

const bulb: Device = {
  id: "bulb",
  protocol: "zigbee",
  name: "Bulb",
  model: "M",
  manufacturer: "ACME",
  type: "BULB",
  capabilities: ["on_off", "brightness", "color", "color_temp"],
  online: true,
  last_seen: null,
  state: { power: true, hex_color: "#ff8800" },
};

test("a scene action keeps the fade of its color", () => {
  const row = rowFromAction({ device_id: "bulb", power: true, hex_color: "#ff0000", transition_time: 3 });
  expect(row.fade).toBe(3);
  expect(actionFromRow(bulb, row)).toMatchObject({ hex_color: "#ff0000", transition_time: 3 });
});

test("no fade is sent for an instant change, nor when the light goes off", () => {
  const instant = rowFromAction({ device_id: "bulb", power: true, hex_color: "#ff0000" });
  expect(actionFromRow(bulb, instant)).not.toHaveProperty("transition_time");
  const off = { ...rowFromAction({ device_id: "bulb", power: true, hex_color: "#ff0000", transition_time: 3 }), power: false };
  expect(actionFromRow(bulb, off)).toEqual({ device_id: "bulb", power: false });
});

test("a sequence reads as its steps", () => {
  const sequence: Sequence = {
    id: 1,
    name: "Party",
    loop: true,
    enabled: true,
    running: false,
    steps: [
      { scene_id: 1, duration: 2 },
      { scene_id: 2, duration: 5 },
    ],
  };
  const name = (id: number) => (id === 1 ? "Red" : "Green");
  expect(describeSteps(sequence, name, "s")).toBe("Red 2 s → Green 5 s");
});

test("a bento tile takes the color of a light that is on", () => {
  expect(tileColor(bulb)).toBe("#ff8800");
  expect(tileColor({ ...bulb, state: { power: false, hex_color: "#ff8800" } })).toBeNull();
});
