import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Device, LightsOrder } from "../../api/types";
import { useDebouncedCallback } from "../../hooks/useDebouncedCallback";
import { brightnessToPercent, percentToBrightness, UI_FADE_SECONDS } from "../../utils/color";
import { CSlider } from "../subcomponents/actions/CSlider";

const switchable = (devices: Device[]) => devices.filter((d) => d.capabilities.includes("on_off"));
const dimmable = (devices: Device[]) => switchable(devices).filter((d) => d.capabilities.includes("brightness"));

/** True when at least one light or socket is on: the button then switches them all off. */
export const anyOn = (devices: Device[]): boolean => switchable(devices).some((d) => d.state.power === true);

/** Average brightness (percent) of the lights that are on, or of all of them when none is. */
export function averageBrightness(devices: Device[]): number {
  const lights = dimmable(devices);
  const lit = lights.filter((d) => d.state.power === true);
  const counted = lit.length > 0 ? lit : lights;
  if (counted.length === 0) return 100;
  const total = counted.reduce((sum, d) => sum + brightnessToPercent(d.state.brightness), 0);
  return Math.round(total / counted.length);
}

export interface CLightsControlsProps {
  /** The devices the controls act on: the lights of a room or a group, or every device of the home. */
  devices: Device[];
  onOrder: (order: LightsOrder) => void;
  /** Names what the controls act on ("Living room") for screen readers. */
  label: string;
}

/**
 * The quick controls of a room, a group or the whole home, like the ones on each device of the home page:
 * an on/off button (off when anything is on) and a brightness slider. To be put in a wrapping flex row.
 */
export function CLightsControls({ devices, onOrder, label }: CLightsControlsProps) {
  const { t } = useTranslation();
  const lights = switchable(devices);
  const on = anyOn(devices);
  const reported = averageBrightness(devices);
  const [level, setLevel] = useState<number | null>(null); // while the slider is being moved

  useEffect(() => setLevel(null), [reported]); // the lights answered: follow them again

  const sendBrightness = useDebouncedCallback((percent: number) => {
    onOrder({ brightness: percentToBrightness(percent), transition_time: UI_FADE_SECONDS });
  }, 250);

  if (lights.length === 0) return null;
  const shown = level ?? reported;

  return (
    <>
      <button
        type="button"
        aria-pressed={on}
        aria-label={`${t("POWER")} ${label}`}
        title={on ? t("TURN_OFF") : t("TURN_ON")}
        onClick={() => onOrder({ power: !on })}
        className="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center border-2 dark:bg-gray-700 bg-gray-100 dark:border-gray-500 border-gray-200"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} className={`w-6 h-6 ${on ? "stroke-green-500" : "stroke-red-500"}`}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5.636 5.636a9 9 0 1 0 12.728 0M12 3v9" />
        </svg>
      </button>
      {dimmable(devices).length > 0 && (
        <CSlider
          min={1}
          max={100}
          aria-label={`${t("BRIGHTNESS")} ${label}`}
          value={shown}
          onChange={(e) => {
            const percent = Number(e.target.value);
            setLevel(percent); // follow the slider right away
            sendBrightness(percent);
          }}
          valueLabel={`${shown}%`}
          className="basis-full"
        />
      )}
    </>
  );
}
