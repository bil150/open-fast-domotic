import { useTranslation } from "react-i18next";
import { Device } from "../../api/types";
import { CQuickColor } from "../subcomponents/actions/CQuickColor";
import { CQuickPower } from "../subcomponents/actions/CQuickPower";
import { CSlider } from "../subcomponents/actions/CSlider";
import { brightnessToPercent, percentToBrightness } from "../../utils/color";
import { DeviceIcon } from "../subcomponents/display/DeviceIcon";

export interface CDeviceListProps {
  devices: Device[];
  onDeviceClick: (device: Device) => void;
  onToggle?: (device: Device) => void;
  onBrightness?: (device: Device, brightness: number) => void;
}

/** One-line summary of what a device is doing. */
export function deviceSummary(device: Device, t: (key: string) => string): string {
  const { state } = device;
  if (device.type === "TEMPERATURE_SENSOR") {
    return state.temperature != null ? `${state.temperature.toFixed(1)} °C` : "—";
  }
  if (device.type === "BUTTON") {
    return state.last_button?.event ?? t("NO_PRESS_YET");
  }
  if (state.power == null) return "";
  return state.power ? t("ON") : t("OFF");
}

export function CDeviceList(props: CDeviceListProps) {
  const { t } = useTranslation();

  if (props.devices.length === 0) {
    return <p className="p-8 text-center text-gray-500">{t("NO_DEVICES")}</p>;
  }

  return (
    <ul className="flex flex-col space-y-2 p-4 w-full overflow-y-auto">
      {props.devices.map((device) => (
        <li
          key={device.id}
          className="flex flex-wrap items-center gap-2 border-2 border-gray-500 rounded-lg p-4 bg-gradient-to-r dark:from-gray-700 dark:to-gray-900"
        >
          <button
            onClick={() => props.onDeviceClick(device)}
            className="flex-grow min-w-0 flex flex-row space-x-4 items-center text-left rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <span
              className={`flex-shrink-0 ${device.online === false ? "opacity-40" : ""} ${
                device.state.power ? "text-yellow-400" : ""
              }`}
            >
              <DeviceIcon type={device.type} />
            </span>
            <span className="flex-grow min-w-0">
              <span className="block text-lg font-semibold truncate">{device.name}</span>
              <span className="block text-sm text-gray-500">
                {device.online === false ? t("OFFLINE") : deviceSummary(device, t)}
              </span>
            </span>
            {device.state.battery != null && (
              <span className="text-xs text-gray-500">{device.state.battery}%</span>
            )}
          </button>
          <CQuickColor device={device} onOpen={props.onDeviceClick} />
          {props.onToggle && <CQuickPower device={device} onToggle={props.onToggle} />}
          {props.onBrightness && device.capabilities.includes("brightness") && (
            <CSlider
              min={1}
              max={100}
              aria-label={t("BRIGHTNESS")}
              disabled={device.online === false}
              value={brightnessToPercent(device.state.brightness)}
              onChange={(e) => props.onBrightness?.(device, percentToBrightness(Number(e.target.value)))}
              valueLabel={`${brightnessToPercent(device.state.brightness)}%`}
              className="basis-full"
            />
          )}
        </li>
      ))}
    </ul>
  );
}
