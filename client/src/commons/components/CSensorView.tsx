import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import { useNotice } from "../../hooks/useNotice";
import { CNotice } from "../subcomponents/display/CNotice";
import { CDeviceHeader } from "./CDeviceHeader";
import { CDeviceProps } from "./CBulbControl";

/** Temperature sensor: the last reading, battery, and a button to ask for a fresh one. */
export function CSensorView({ device, onListClick, onDeviceChange }: CDeviceProps) {
  const { t } = useTranslation();
  const { notice, show } = useNotice();
  const [refreshing, setRefreshing] = useState(false);
  const { temperature, battery } = device.state;

  async function refresh() {
    setRefreshing(true);
    try {
      onDeviceChange(await api.devices.refresh(device.id));
    } catch (e) {
      show((e as Error).message, "error");
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="page-card">
      <CDeviceHeader
        device={device}
        onListClick={onListClick}
        onDeviceChange={onDeviceChange}
        onError={(message) => show(message, "error")}
      />
      <div className="flex flex-col items-center justify-center flex-grow gap-4 p-6">
        <p className="text-6xl" aria-label={t("TEMPERATURE")}>
          {temperature != null ? `${temperature.toFixed(1)} °C` : "—"}
        </p>
        <dl className="text-sm text-gray-500 text-center space-y-1">
          {battery != null && (
            <div>
              <dt className="inline">{t("BATTERY")}: </dt>
              <dd className="inline">{battery}%</dd>
            </div>
          )}
          {device.last_seen && (
            <div>
              <dt className="inline">{t("LAST_SEEN")}: </dt>
              <dd className="inline">{device.last_seen.replace("T", " ")}</dd>
            </div>
          )}
        </dl>
        <button
          onClick={refresh}
          disabled={refreshing}
          className="border-2 border-gray-400 rounded-full px-6 py-2 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50"
        >
          {t("REFRESH")}
        </button>
        <p className="text-xs text-gray-500 text-center max-w-xs">{t("SENSOR_HINT")}</p>
      </div>
      <CNotice notice={notice} />
    </div>
  );
}
