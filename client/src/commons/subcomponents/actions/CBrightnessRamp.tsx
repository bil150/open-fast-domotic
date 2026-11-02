import { useCallback, useEffect, useRef, useState } from "react";

export interface CBrightnessRampProps {
  brightness: number;
  onChange: (brightnessPercent: number) => void;
  orientation?: "horizontal" | "vertical";
}

const PERCENT_VISIBLE_MS = 2000;

export function CBrightnessRamp({ brightness, onChange, orientation }: CBrightnessRampProps) {
  const horizontal = orientation === "horizontal";
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showPercentage, setShowPercentage] = useState(true);

  const flashPercentage = useCallback(() => {
    setShowPercentage(true);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setShowPercentage(false), PERCENT_VISIBLE_MS);
  }, []);

  const drawGradient = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const { width, height } = canvas;
    const gradient = horizontal
      ? ctx.createLinearGradient(0, 0, width, 0)
      : ctx.createLinearGradient(0, 0, 0, height);

    for (let i = 0; i <= 100; i++) {
      const grey = Math.round(150 + 105 * (i / 100)); // from a darker grey (150) to white (255)
      gradient.addColorStop(i / 100, `rgba(${grey}, ${grey}, ${grey}, 1)`);
    }
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    // the selection line
    const position = (brightness / 100) * (horizontal ? width : height);
    ctx.strokeStyle = "white";
    ctx.lineWidth = 4;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    if (horizontal) {
      ctx.moveTo(position, 0);
      ctx.lineTo(position, height);
    } else {
      ctx.moveTo(0, position);
      ctx.lineTo(width, position);
    }
    ctx.stroke();
  }, [brightness, horizontal]);

  useEffect(() => {
    drawGradient();
  }, [drawGradient]);

  useEffect(() => {
    flashPercentage();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [brightness, flashPercentage]);

  /** Brightness from a pointer position, 0..100. */
  const update = useCallback(
    (clientX: number, clientY: number) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const position = horizontal ? clientX - rect.left : clientY - rect.top;
      const size = horizontal ? rect.width : rect.height;
      onChange(Math.max(0, Math.min(100, (position / size) * 100)));
      flashPercentage();
    },
    [horizontal, onChange, flashPercentage]
  );

  useEffect(() => {
    if (!isDragging) return undefined;
    const onMove = (e: MouseEvent) => requestAnimationFrame(() => update(e.clientX, e.clientY));
    const onUp = () => setIsDragging(false);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [isDragging, update]);

  return (
    <div
      className="relative flex flex-col items-center"
      onMouseUp={() => setIsDragging(false)}
      onMouseLeave={() => setIsDragging(false)}
    >
      <canvas
        ref={canvasRef}
        width={horizontal ? 300 : 50}
        height={horizontal ? 50 : 300}
        className="cursor-pointer rounded-3xl border-4 dark:border-gray-500 border-gray-200"
        onMouseDown={(e) => {
          setIsDragging(true);
          update(e.clientX, e.clientY);
        }}
        onTouchMove={(e) => {
          const touch = e.touches[0];
          if (touch) update(touch.clientX, touch.clientY);
        }}
      />
      <div
        className={`absolute inset-0 flex items-center justify-center transition-opacity duration-1000 ${
          showPercentage ? "opacity-100" : "opacity-0"
        } pointer-events-none`}
      >
        <span className="text-white text-lg font-bold">{Math.round(brightness)}%</span>
      </div>
    </div>
  );
}

export default CBrightnessRamp;
