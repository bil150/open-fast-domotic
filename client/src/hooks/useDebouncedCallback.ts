import { useCallback, useEffect, useRef } from "react";

/** Calls `callback` once the arguments stopped changing for `delay` ms (sliders, color picker). */
export function useDebouncedCallback<A extends unknown[]>(
  callback: (...args: A) => void,
  delay = 200
): (...args: A) => void {
  const latest = useRef(callback);
  const timer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    latest.current = callback;
  }, [callback]);

  useEffect(() => () => clearTimeout(timer.current), []);

  return useCallback(
    (...args: A) => {
      clearTimeout(timer.current);
      timer.current = setTimeout(() => latest.current(...args), delay);
    },
    [delay]
  );
}
