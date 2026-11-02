import { CSSProperties, InputHTMLAttributes } from "react";

export interface CSliderProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "className"> {
  /** Applied to the container: give it a width. */
  className?: string;
  /** Text shown in the middle of the bar, e.g. "60%". */
  valueLabel?: string;
}

/** A range input styled like the brightness ramp, the same in Chrome, Safari and Firefox (see .slider in index.css). */
export function CSlider({ className = "", valueLabel, ...props }: CSliderProps) {
  const min = Number(props.min ?? 0);
  const max = Number(props.max ?? 100);
  const value = Number(props.value ?? props.defaultValue ?? min);
  const progress = max > min ? ((value - min) / (max - min)) * 100 : 0;

  return (
    <div className={`relative ${className}`}>
      <input
        {...props}
        type="range"
        className="slider w-full"
        style={{ "--p": `${Math.max(0, Math.min(100, progress))}%` } as CSSProperties}
      />
      {valueLabel && (
        <span className="absolute inset-0 flex items-center justify-center pointer-events-none text-sm font-bold text-white drop-shadow">
          {valueLabel}
        </span>
      )}
    </div>
  );
}
