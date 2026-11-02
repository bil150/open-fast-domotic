import { useEffect, useMemo, useRef } from "react";

export interface Throttled<A extends unknown[]> {
  (...args: A): void;
  cancel: () => void;
}

/**
 * Runs `callback` at most once every `delay` ms while it keeps being called (dragging a color picker),
 * always finishing with the last arguments. The first call goes through at once.
 */
export function createThrottle<A extends unknown[]>(callback: (...args: A) => void, delay: number): Throttled<A> {
  let lastRun = Number.NEGATIVE_INFINITY;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let pending: A | null = null;

  const run = (args: A) => {
    lastRun = Date.now();
    pending = null;
    callback(...args);
  };

  const throttled = ((...args: A) => {
    const wait = delay - (Date.now() - lastRun);
    if (wait <= 0) {
      clearTimeout(timer);
      timer = undefined;
      run(args);
      return;
    }
    pending = args;
    if (timer === undefined) {
      timer = setTimeout(() => {
        timer = undefined;
        if (pending) run(pending);
      }, wait);
    }
  }) as Throttled<A>;

  throttled.cancel = () => {
    clearTimeout(timer);
    timer = undefined;
    pending = null;
  };
  return throttled;
}

/** Hook version of createThrottle: always calls the latest `callback`. */
export function useThrottledCallback<A extends unknown[]>(
  callback: (...args: A) => void,
  delay = 250
): (...args: A) => void {
  const latest = useRef(callback);
  useEffect(() => {
    latest.current = callback;
  }, [callback]);

  const throttled = useMemo(() => createThrottle((...args: A) => latest.current(...args), delay), [delay]);
  useEffect(() => () => throttled.cancel(), [throttled]);
  return throttled;
}
