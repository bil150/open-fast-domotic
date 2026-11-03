import { afterEach, expect, test, vi } from "vitest";
import { api, ApiError, errorMessage } from "./client";

afterEach(() => {
  vi.restoreAllMocks();
});

function mockFetch(status: number, body?: unknown) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "Status text",
    json: async () => body,
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

test("errorMessage reads a plain FastAPI detail", () => {
  expect(errorMessage({ detail: "The device did not answer" }, "x")).toBe("The device did not answer");
});

test("errorMessage joins validation errors", () => {
  const body = { detail: [{ loc: ["body", "hue"], msg: "must be given with saturation" }] };
  expect(errorMessage(body, "x")).toBe("hue must be given with saturation");
});

test("errorMessage falls back", () => {
  expect(errorMessage(null, "fallback")).toBe("fallback");
});

test("devices.list unwraps the devices", async () => {
  const fetchMock = mockFetch(200, { devices: [{ id: "a" }] });
  expect(await api.devices.list()).toEqual([{ id: "a" }]);
  expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/devices");
});

test("light sends a PATCH with the body", async () => {
  const fetchMock = mockFetch(200, { id: "a" });
  await api.devices.light("00:11:22", { power: true, brightness: 120 });
  const [url, init] = fetchMock.mock.calls[0] ?? [];
  expect(url).toBe("/api/v1/devices/00%3A11%3A22/light");
  expect(init?.method).toBe("PATCH");
  expect(JSON.parse(init?.body)).toEqual({ power: true, brightness: 120 });
});

test("a failing request throws an ApiError with the server's message", async () => {
  mockFetch(502, { detail: "The device did not answer" });
  await expect(api.devices.toggle("a")).rejects.toMatchObject({
    status: 502,
    message: "The device did not answer",
  });
  mockFetch(404, { detail: "Unknown scene 3" });
  await expect(api.scenes.apply(3)).rejects.toBeInstanceOf(ApiError);
});

test("204 answers resolve to undefined", async () => {
  mockFetch(204);
  await expect(api.scenes.remove(1)).resolves.toBeUndefined();
  await expect(api.devices.remove("a4:c1")).resolves.toBeUndefined();
});

test("scenes.apply returns the per-device results", async () => {
  mockFetch(200, { results: { a: true, b: false } });
  expect(await api.scenes.apply(1)).toEqual({ a: true, b: false });
});
