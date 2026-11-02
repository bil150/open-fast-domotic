import { useTranslation } from "react-i18next";
import { Device } from "../../api/types";
import { brightnessToPercent, percentToBrightness } from "../../utils/color";
import { CQuickColor, deviceColor } from "../subcomponents/actions/CQuickColor";
import { CQuickPower } from "../subcomponents/actions/CQuickPower";
import { DeviceIcon } from "../subcomponents/display/DeviceIcon";
import { deviceSummary } from "./CDeviceList";
import { CSlider } from "../subcomponents/actions/CSlider";

export interface CDeviceBentoProps {
  devices: Device[];
  onDeviceClick: (device: Device) => void;
  onToggle: (device: Device) => void;
  onBrightness: (device: Device, brightness: number) => void;
}

/** The current color of a light that is on, used to tint its tile. */
export function tileColor(device: Device): string | null {
  return device.state.power === true ? deviceColor(device) : null;
}

/** Bento layout: dimmable lights get wide tiles with a brightness slider, sensors show their reading big. */
export function CDeviceBento({ devices, onDeviceClick, onToggle, onBrightness }: CDeviceBentoProps) {
  const { t } = useTranslation();

  if (devices.length === 0) {
    return <p className="p-8 text-center text-gray-500">{t("NO_DEVICES")}</p>;
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 auto-rows-[8rem] grid-flow-dense gap-3 p-4 w-full overflow-y-auto">
      {devices.map((device) => {
        const dimmable = device.capabilities.includes("brightness");
        const sensor = device.type === "TEMPERATURE_SENSOR";
        const tint = tileColor(device);
        return (
          <div
            key={device.id}
            className={`${dimmable ? "col-span-2" : ""} relative flex flex-col justify-between rounded-2xl border-2 border-gray-500 p-3 bg-gradient-to-br dark:from-gray-700 dark:to-gray-900 ${
              device.online === false ? "opacity-50" : ""
            }`}
            style={tint ? { borderColor: tint, boxShadow: `0 0 18px -6px ${tint}` } : undefined}
          >
            <button
              onClick={() => onDeviceClick(device)}
              className="flex items-start gap-2 text-left min-w-0 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
            >
              <span className={`flex-shrink-0 ${device.state.power ? "text-yellow-400" : ""}`} style={tint ? { color: tint } : undefined}>
                <DeviceIcon type={device.type} />
              </span>
              <span className="min-w-0">
                <span className="block font-semibold truncate">{device.name}</span>
                <span className="block text-xs text-gray-500">
                  {device.online === false ? t("OFFLINE") : sensor ? "" : deviceSummary(device, t)}
                </span>
              </span>
            </button>

            {sensor && <span className="text-3xl font-semibold">{deviceSummary(device, t)}</span>}

            <div className="flex items-center gap-2">
              {dimmable ? (
                <CSlider
                  min={1}
                  max={100}
                  aria-label={t("BRIGHTNESS")}
                  disabled={device.online === false}
                  value={brightnessToPercent(device.state.brightness)}
                  onChange={(e) => onBrightness(device, percentToBrightness(Number(e.target.value)))}
                  valueLabel={`${brightnessToPercent(device.state.brightness)}%`}
                  className="flex-grow min-w-0"
                />
              ) : (
                <span className="flex-grow" />
              )}
              {device.state.battery != null && <span className="text-xs text-gray-500">{device.state.battery}%</span>}
              <CQuickColor device={device} onOpen={onDeviceClick} />
              <CQuickPower device={device} onToggle={onToggle} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
