import { useTranslation } from "react-i18next";
import { Device } from "../../../api/types";
import { kelvinToRgb, rgbToHex } from "../../../utils/color";

/** The color a light currently has (colored or white), whether it is on or off. Null when unknown. */
export function deviceColor(device: Device): string | null {
  const { state } = device;
  if (state.hex_color) return state.hex_color;
  if (state.color_temp_kelvin) return rgbToHex(kelvinToRgb(state.color_temp_kelvin));
  return null;
}

/** Color swatch of a light; opens the bulb page, where the color is picked. */
export function CQuickColor({ device, onOpen }: { device: Device; onOpen: (device: Device) => void }) {
  const { t } = useTranslation();
  if (!device.capabilities.includes("color") && !device.capabilities.includes("color_temp")) return null;
  const color = deviceColor(device);
  const on = device.state.power === true;

  return (
    <button
      type="button"
      aria-label={`${t("CHANGE_COLOR")} ${device.name}`}
      title={t("CHANGE_COLOR")}
      onClick={(e) => {
        e.stopPropagation();
        onOpen(device);
      }}
      className={`flex-shrink-0 w-12 h-12 rounded-full border-2 border-gray-300 dark:border-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 ${on ? "" : "opacity-50"}`}
      style={{ background: color ?? "conic-gradient(red, yellow, lime, cyan, blue, magenta, red)" }}
    />
  );
}
