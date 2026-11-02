import { useCallback, useEffect, useRef, useState } from "react";

export interface Notice {
  text: string;
  kind: "ok" | "error";
}

/** A message shown for a few seconds (see CNotice). */
export function useNotice(duration = 4000) {
  const [notice, setNotice] = useState<Notice | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => () => clearTimeout(timer.current), []);

  const show = useCallback(
    (text: string, kind: Notice["kind"] = "ok") => {
      clearTimeout(timer.current);
      setNotice({ text, kind });
      timer.current = setTimeout(() => setNotice(null), duration);
    },
    [duration]
  );

  return { notice, show };
}
