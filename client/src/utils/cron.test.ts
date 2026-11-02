import { expect, test } from "vitest";
import { buildCron, describeCron, parseCron } from "./cron";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

test("buildCron: a time on some days", () => {
  expect(buildCron({ time: "07:30", days: [1, 2, 3, 4, 5] })).toBe("30 7 * * 1,2,3,4,5");
});

test("buildCron: no day or all days means every day", () => {
  expect(buildCron({ time: "22:05", days: [] })).toBe("5 22 * * *");
  expect(buildCron({ time: "22:05", days: [0, 1, 2, 3, 4, 5, 6] })).toBe("5 22 * * *");
});

test("buildCron: days are sorted and deduplicated", () => {
  expect(buildCron({ time: "08:00", days: [3, 1, 3] })).toBe("0 8 * * 1,3");
});

test("parseCron reads what buildCron writes", () => {
  expect(parseCron("30 7 * * 1,2,3")).toEqual({ time: "07:30", days: [1, 2, 3] });
  expect(parseCron("5 22 * * *")).toEqual({ time: "22:05", days: [0, 1, 2, 3, 4, 5, 6] });
  expect(parseCron("0 6 * * 7")).toEqual({ time: "06:00", days: [0] }); // 7 = Sunday too
});

test("parseCron refuses what the simple editor cannot represent", () => {
  expect(parseCron("*/5 * * * *")).toBeNull();
  expect(parseCron("30 7 1 * *")).toBeNull();
  expect(parseCron("30 7 * * 1-5")).toBeNull();
  expect(parseCron("61 7 * * *")).toBeNull();
  expect(parseCron("30 7 * *")).toBeNull();
});

test("describeCron", () => {
  expect(describeCron("30 7 * * 1,2", DAYS, "Every day")).toBe("07:30 · Mon Tue");
  expect(describeCron("30 7 * * *", DAYS, "Every day")).toBe("07:30 · Every day");
  expect(describeCron("*/5 * * * *", DAYS, "Every day")).toBe("*/5 * * * *");
});
