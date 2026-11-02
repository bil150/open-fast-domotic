import React, { useRef, useEffect, useState, useCallback } from "react";
import { ColorRGB } from "../../../types/ColorRGB";

export interface CColorPickerProps {
  onChange?: (color: ColorRGB) => void;
  color: ColorRGB;
  size?: number; // Add size prop
}

export function CColorPicker(props: CColorPickerProps) {
  const { size = 400 } = props; // Default size to 400 if not provided
  const [pointerPosition, setPointerPosition] = useState<{ x: number, y: number } | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const isDragging = useRef(false);


  const renderColorCircle = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const radius = canvas.width / 2;
    const toRad = (deg: number) => (deg * Math.PI) / 180;

    // Draw hue circle
    for (let angle = 0; angle < 360; angle += 1) {
      const startAngle = toRad(angle);
      const endAngle = toRad(angle + 1);
      ctx.beginPath();
      ctx.moveTo(radius, radius);
      ctx.arc(radius, radius, radius, startAngle, endAngle);
      ctx.closePath();
      ctx.fillStyle = `hsl(${angle}, 100%, 50%)`;
      ctx.fill();
    }

    // Draw brightness gradient with more white in the center
    const gradient = ctx.createRadialGradient(radius, radius, 0, radius, radius, radius);
    gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
    gradient.addColorStop(0.5, 'rgba(255, 255, 255, 0.7)');
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0.0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }, []);

  useEffect(() => {
    renderColorCircle();
  }, [renderColorCircle, size]);

  const { onChange } = props;

  const handleColorChange = useCallback((clientX: number, clientY: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const { left, top } = canvas.getBoundingClientRect();
    const offsetX = (clientX - left) * devicePixelRatio;
    const offsetY = (clientY - top) * devicePixelRatio;
    const radius = canvas.width / 2;
    const distance = Math.sqrt((offsetX - radius) ** 2 + (offsetY - radius) ** 2);

    // Check if the click is within the circle
    if (distance > radius) return;

    const imageData = ctx.getImageData(offsetX, offsetY, 1, 1).data;
    const [red = 0, green = 0, blue = 0] = Array.from(imageData);
    onChange?.({ red, green, blue }); // only on user action, never on mount
    setPointerPosition({ x: offsetX / devicePixelRatio, y: offsetY / devicePixelRatio });
  }, [onChange]);

  // Pointer events cover mouse, finger and pen. The pointer is captured so the drag keeps going
  // when it leaves the circle, and touch-action: none (below) stops the browser from scrolling the
  // page instead of letting the finger move the color.
  const handlePointerDown = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    isDragging.current = true;
    e.currentTarget.setPointerCapture(e.pointerId);
    handleColorChange(e.clientX, e.clientY);
  }, [handleColorChange]);

  const handlePointerMove = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    if (isDragging.current) handleColorChange(e.clientX, e.clientY);
  }, [handleColorChange]);

  const handlePointerUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  return (
    <div className="relative flex flex-col items-center">
      <canvas
        ref={canvasRef}
        width={size * devicePixelRatio} // Adjust width based on size prop
        height={size * devicePixelRatio} // Adjust height based on size prop
        style={{ width: size, height: size, touchAction: 'none' }} // Set the CSS size to the desired size
        className="cursor-pointer rounded-full border-4 dark:border-gray-500 border-gray-200"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      />
      {pointerPosition && (
        <div
          className="absolute w-8 h-8 rounded-full border-4 border-dotted border-gray-500"
          style={{
            left: pointerPosition.x - 16,
            top: pointerPosition.y - 16,
            pointerEvents: 'none',
          }}
        />
      )}
    </div>
  );
}

export default CColorPicker;