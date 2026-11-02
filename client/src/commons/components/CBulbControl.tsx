import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import { Device, EffectName, LightRequest } from "../../api/types";
import { useDebouncedCallback } from "../../hooks/useDebouncedCallback";
import { useThrottledCallback } from "../../hooks/useThrottledCallback";
import { useNotice } from "../../hooks/useNotice";
import { ColorRGB } from "../../types/ColorRGB";
import {
  brightnessToPercent,
  hexToRgb,
  kelvinToRgb,
  percentToBrightness,
  rgbToHex,
  UI_FADE_SECONDS,
} from "../../utils/color";
import { CBrightnessRamp } from "../subcomponents/actions/CBrightnessRamp";
import { CColorPicker } from "../subcomponents/actions/CColorPicker";
import { CPowerBtn } from "../subcomponents/actions/CPowerBtn";
import { CColorPastille } from "../subcomponents/display/CColorPastille";
import { CNotice } from "../subcomponents/display/CNotice";
import { CDeviceHeader } from "./CDeviceHeader";
import { CSlider } from "../subcomponents/actions/CSlider";

export interface CDeviceProps {
  device: Device;
  onListClick: () => void;
  onDeviceChange: (device: Device) => void;
}

type Mode = "color" | "white";

/** Heroicons "sparkles" (outline). */
function SparklesIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
      />
    </svg>
  );
}

const EFFECTS: { name: EffectName; emoji: string; label: string }[] = [
  { name: "fire", emoji: "🔥", label: "FX_FIRE" },
  { name: "candle", emoji: "🕯️", label: "FX_CANDLE" },
];

const DEFAULT_KELVIN_RANGE: [number, number] = [2000, 6500];

/** Bulbs and sockets: power, and when the device supports it brightness, color and white. */
export function CBulbControl(props: CDeviceProps) {
  const { t } = useTranslation();
  const { device, onDeviceChange } = props;
  const { notice, show } = useNotice();

  const canColor = device.capabilities.includes("color");
  const canWhite = device.capabilities.includes("color_temp");
  const canDim = device.capabilities.includes("brightness");
  const [minKelvin, maxKelvin] = device.color_temp_range_kelvin ?? DEFAULT_KELVIN_RANGE;

  const [mode, setMode] = useState<Mode>(canColor ? "color" : "white");
  const [color, setColor] = useState<ColorRGB>(hexToRgb(device.state.hex_color ?? "#ffffff"));
  const [brightness, setBrightness] = useState(brightnessToPercent(device.state.brightness));
  const [kelvin, setKelvin] = useState(device.state.color_temp_kelvin ?? Math.round((minKelvin + maxKelvin) / 2));
  const [pending, setPending] = useState(false);
  const [effect, setEffect] = useState<EffectName | null>(null);
  const [fxOpen, setFxOpen] = useState(false);

  // follow the real state (live updates, scenes, buttons...)
  useEffect(() => {
    if (!effect && device.state.brightness != null) setBrightness(brightnessToPercent(device.state.brightness));
  }, [device.state.brightness, effect]);

  // the effect runs on the server and survives leaving this page
  useEffect(() => {
    if (!canDim) return;
    api.devices.effect(device.id).then(setEffect).catch(() => undefined);
  }, [device.id, canDim]);
  useEffect(() => {
    if (device.state.color_temp_kelvin) setKelvin(device.state.color_temp_kelvin);
  }, [device.state.color_temp_kelvin]);

  const send = useCallback(
    async (body: LightRequest) => {
      setEffect(null); // any manual command stops an effect on the server
      try {
        onDeviceChange(await api.devices.light(device.id, body));
      } catch (e) {
        show((e as Error).message, "error");
      } finally {
        setPending(false);
      }
    },
    [device.id, onDeviceChange, show]
  );

  // while the finger moves, the light follows (a few times per second), then ends on the last color
  const sendColor = useThrottledCallback((rgb: ColorRGB) => send({ power: true, hex_color: rgbToHex(rgb), transition_time: UI_FADE_SECONDS }));
  const sendBrightness = useDebouncedCallback((percent: number) =>
    send({ brightness: percentToBrightness(percent), transition_time: UI_FADE_SECONDS })
  );
  const sendKelvin = useDebouncedCallback((value: number) =>
    send({ power: true, color_temp_kelvin: value, transition_time: UI_FADE_SECONDS })
  );

  const onColor = (rgb: ColorRGB) => {
    setColor(rgb);
    setPending(true);
    sendColor(rgb);
  };
  const onBrightness = (percent: number) => {
    setBrightness(percent);
    sendBrightness(percent);
  };
  const onKelvin = (value: number) => {
    setKelvin(value);
    sendKelvin(value);
  };

  async function chooseEffect(next: EffectName | null) {
    setFxOpen(false);
    try {
      if (next) await api.devices.startEffect(device.id, next, Math.max(1, percentToBrightness(brightness)));
      else await api.devices.stopEffect(device.id);
      setEffect(next);
    } catch (e) {
      show((e as Error).message, "error");
    }
  }

  const preview = mode === "white" ? kelvinToRgb(kelvin) : color;

  return (
    <div className="page-card">
      <CDeviceHeader
        device={device}
        onListClick={props.onListClick}
        onDeviceChange={props.onDeviceChange}
        onError={(message) => show(message, "error")}
      />
      {device.online === false && (
        <p className="mx-4 md:mx-6 mb-2 text-center text-sm text-red-500">{t("OFFLINE")}</p>
      )}

      <div className="flex flex-col md:flex-row justify-center items-center gap-4 p-4 md:p-8">
        <div className="space-y-4 flex flex-col items-center">
          {canColor && canWhite && (
            <div role="tablist" className="flex rounded-full border-2 border-gray-400 overflow-hidden">
              {(["color", "white"] as Mode[]).map((m) => (
                <button
                  key={m}
                  role="tab"
                  aria-selected={mode === m}
                  onClick={() => setMode(m)}
                  className={`px-4 py-1 ${mode === m ? "bg-gray-500 text-white" : ""}`}
                >
                  {t(m === "color" ? "COLOR" : "WHITE")}
                </button>
              ))}
            </div>
          )}

          {mode === "color" && canColor && <CColorPicker size={260} color={color} onChange={onColor} />}

          {mode === "white" && canWhite && (
            <div className="w-full max-w-[260px] space-y-2">
              <CSlider
                aria-label={t("WHITE")}
                min={minKelvin}
                max={maxKelvin}
                step={50}
                value={kelvin}
                onChange={(e) => onKelvin(Number(e.target.value))}
                valueLabel={`${kelvin} K`}
                className="w-full"
              />
            </div>
          )}

          {canDim && <CBrightnessRamp brightness={brightness} orientation="horizontal" onChange={onBrightness} />}
        </div>

        <div className="flex flex-row md:flex-col items-center gap-4">
          {(canColor || canWhite) && <CColorPastille color={preview} />}
          <CPowerBtn
            power={!!device.state.power}
            disabled={pending}
            onToggle={(power) => send({ power })}
          />
          {canDim && (
            <div className="relative">
              <button
                onClick={() => setFxOpen((open) => !open)}
                aria-label={t("FX")}
                aria-expanded={fxOpen}
                title={t("FX")}
                className={`w-12 h-12 rounded-full border-2 flex items-center justify-center ${
                  effect ? "bg-gray-500 border-gray-500 text-white" : "border-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                }`}
              >
                <SparklesIcon />
              </button>
              {fxOpen && (
                <ul
                  role="menu"
                  className="absolute z-10 right-0 md:right-auto md:left-14 top-14 md:top-0 w-44 rounded-lg shadow-lg border-2 border-gray-400 bg-white text-black dark:bg-gray-700 dark:text-gray-200 p-1"
                >
                  <li>
                    <button role="menuitem" onClick={() => chooseEffect(null)} className="w-full text-left px-3 py-2 hover:bg-gray-200 dark:hover:bg-gray-600">
                      {t("FX_NONE")}
                    </button>
                  </li>
                  {EFFECTS.map((fx) => (
                    <li key={fx.name}>
                      <button
                        role="menuitemradio"
                        aria-checked={effect === fx.name}
                        onClick={() => chooseEffect(fx.name)}
                        className={`w-full text-left px-3 py-2 hover:bg-gray-200 dark:hover:bg-gray-600 ${effect === fx.name ? "font-bold" : ""}`}
                      >
                        {fx.emoji} {t(fx.label)}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>
      <CNotice notice={notice} />
    </div>
  );
}

export default CBulbControl;
