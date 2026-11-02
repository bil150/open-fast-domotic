import { useTranslation } from "react-i18next";
import { Device } from "../../../api/types";

/** Small on/off button for a list row or a bento tile. Renders nothing for devices that cannot switch. */
export function CQuickPower({ device, onToggle }: { device: Device; onToggle: (device: Device) => void }) {
  const { t } = useTranslation();
  if (!device.capabilities.includes("on_off")) return null;
  const on = device.state.power === true;
  return (
    <button
      type="button"
      aria-pressed={on}
      aria-label={`${t("POWER")} ${device.name}`}
      title={on ? t("TURN_OFF") : t("TURN_ON")}
      disabled={device.online === false}
      onClick={(e) => {
        e.stopPropagation();
        onToggle(device);
      }}
      className="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center border-2 dark:bg-gray-700 bg-gray-100 dark:border-gray-500 border-gray-200 disabled:opacity-40"
    >
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} className={`w-6 h-6 ${on ? "stroke-green-500" : "stroke-red-500"}`}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5.636 5.636a9 9 0 1 0 12.728 0M12 3v9" />
      </svg>
    </button>
  );
}
