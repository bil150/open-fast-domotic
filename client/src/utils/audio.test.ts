import { describe, expect, it } from "vitest";
import { createBeatDetector, levelToBrightness, rmsLevel, smoothLevel } from "./audio";

describe("rmsLevel", () => {
  it("is 0 for silence and for an empty frame", () => {
    expect(rmsLevel(new Uint8Array(64).fill(128))).toBe(0);
    expect(rmsLevel(new Uint8Array(0))).toBe(0);
  });

  it("is about 1 for a full-scale square wave", () => {
    expect(rmsLevel(Uint8Array.from([0, 255, 0, 255]))).toBeCloseTo(1, 1);
  });
});

describe("smoothLevel", () => {
  it("rises faster than it falls", () => {
    const up = smoothLevel(0, 1);
    const down = 1 - smoothLevel(1, 0);
    expect(up).toBeGreaterThan(down);
  });
});

describe("levelToBrightness", () => {
  it("stays within 5..255 and never goes fully dark", () => {
    expect(levelToBrightness(0, 1)).toBe(5);
    expect(levelToBrightness(1, 1)).toBe(255);
    expect(levelToBrightness(1, 10)).toBe(255);
  });

  it("amplifies quiet sources with the sensitivity", () => {
    expect(levelToBrightness(0.1, 4)).toBeGreaterThan(levelToBrightness(0.1, 1));
  });
});

describe("createBeatDetector", () => {
  it("fires on a jump, then stays silent on a steady sound", () => {
    const beat = createBeatDetector();
    for (let t = 0; t < 3000; t += 16) beat(0.3, t); // settles
    let fired = 0;
    for (let t = 3000; t < 5000; t += 16) if (beat(0.3, t)) fired++;
    expect(fired).toBe(0);
    expect(beat(0.9, 5100)).toBe(true);
  });

  it("waits a minimum gap between two beats", () => {
    const beat = createBeatDetector(200);
    for (let t = 0; t < 1000; t += 16) beat(0.05, t);
    expect(beat(0.9, 1000)).toBe(true);
    expect(beat(0.2, 1050)).toBe(false);
    expect(beat(1, 1100)).toBe(false); // too soon
  });

  it("stays silent below the floor", () => {
    const beat = createBeatDetector();
    expect(beat(0.02, 0)).toBe(false);
  });
});
