import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { createThrottle } from "./useThrottledCallback";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

test("the first call goes through, the following ones are spaced and end on the last value", () => {
  const callback = vi.fn();
  const throttled = createThrottle(callback, 250);

  throttled(1);
  expect(callback).toHaveBeenCalledTimes(1);

  vi.advanceTimersByTime(100);
  throttled(2);
  throttled(3);
  expect(callback).toHaveBeenCalledTimes(1); // too soon

  vi.advanceTimersByTime(150);
  expect(callback).toHaveBeenCalledTimes(2);
  expect(callback).toHaveBeenLastCalledWith(3); // the intermediate value 2 is dropped

  vi.advanceTimersByTime(1000);
  expect(callback).toHaveBeenCalledTimes(2); // nothing pending: nothing more
});

test("cancel drops the pending call", () => {
  const callback = vi.fn();
  const throttled = createThrottle(callback, 250);
  throttled(1);
  throttled(2);
  throttled.cancel();
  vi.advanceTimersByTime(1000);
  expect(callback).toHaveBeenCalledTimes(1);
});
