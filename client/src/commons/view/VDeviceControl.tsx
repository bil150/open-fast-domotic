import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import { Device } from "../../api/types";
import { useDebouncedCallback } from "../../hooks/useDebouncedCallback";
import { UI_FADE_SECONDS } from "../../utils/color";
import { useDevices } from "../../hooks/useDevices";
import { useNotice } from "../../hooks/useNotice";
import { CBulbControl } from "../components/CBulbControl";
import { CButtonView } from "../components/CButtonView";
import { CDeviceBento } from "../components/CDeviceBento";
import { CDeviceList } from "../components/CDeviceList";
import { CSensorView } from "../components/CSensorView";
import { CNotice } from "../subcomponents/display/CNotice";

const PAIRING_SECONDS = 60;

type Layout = "list" | "bento";
const LAYOUT_KEY = "deviceLayout";

function savedLayout(): Layout {
  try {
    return localStorage.getItem(LAYOUT_KEY) === "bento" ? "bento" : "list";
  } catch {
    return "list";
  }
}

export function VDeviceControl() {
  const { t } = useTranslation();
  const { devices, loading, error, connected, replace } = useDevices();
  const { notice, show } = useNotice();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pairing, setPairing] = useState(0);
  const [layout, setLayout] = useState<Layout>(savedLayout);

  function chooseLayout(next: Layout) {
    setLayout(next);
    try {
      localStorage.setItem(LAYOUT_KEY, next);
    } catch {
      /* storage unavailable: the choice just is not remembered */
    }
  }

  async function toggleDevice(device: Device) {
    try {
      replace(await api.devices.toggle(device.id));
    } catch (e) {
      show((e as Error).message, "error");
    }
  }

  const sendBrightness = useDebouncedCallback(async (device: Device, brightness: number) => {
    try {
      replace(await api.devices.light(device.id, { power: true, brightness, transition_time: UI_FADE_SECONDS }));
    } catch (e) {
      show((e as Error).message, "error");
    }
  }, 250);

  function setBrightness(device: Device, brightness: number) {
    replace({ ...device, state: { ...device.state, power: true, brightness } }); // follow the slider right away
    sendBrightness(device, brightness);
  }

  // count down while the coordinator lets new devices pair
  useEffect(() => {
    if (pairing <= 0) return;
    const timer = setTimeout(() => setPairing((s) => s - 1), 1000);
    return () => clearTimeout(timer);
  }, [pairing]);

  async function startPairing() {
    try {
      await api.coordinator.discover(PAIRING_SECONDS);
      setPairing(PAIRING_SECONDS);
    } catch (e) {
      show((e as Error).message, "error");
    }
  }

  // always show the freshest copy of the selected device
  const selected = devices.find((d) => d.id === selectedId) ?? null;
  const back = () => setSelectedId(null);

  if (selected) {
    const common = { device: selected, onListClick: back, onDeviceChange: replace };
    return (
      <>
        {selected.type === "TEMPERATURE_SENSOR" && <CSensorView {...common} />}
        {selected.type === "BUTTON" && <CButtonView {...common} allDevices={devices} />}
        {selected.type !== "TEMPERATURE_SENSOR" && selected.type !== "BUTTON" && <CBulbControl {...common} />}
      </>
    );
  }

  return (
    <div className="page-card">
      <div className="flex flex-wrap justify-between items-center gap-2 px-4 md:px-6 py-2">
        <h2 className="text-2xl">{t("DEVICES")}</h2>
        <div className="flex items-center gap-2">
        <div role="group" aria-label={t("LAYOUT")} className="flex border-2 border-gray-300 dark:border-gray-600 rounded-full overflow-hidden text-sm">
          {(["list", "bento"] as const).map((name) => (
            <button
              key={name}
              aria-pressed={layout === name}
              onClick={() => chooseLayout(name)}
              className={`px-3 py-2 ${layout === name ? "bg-gray-500 text-white" : "hover:bg-gray-200 dark:hover:bg-gray-700"}`}
            >
              {t(name === "list" ? "LAYOUT_LIST" : "LAYOUT_BENTO")}
            </button>
          ))}
        </div>
        <button
          onClick={startPairing}
          disabled={pairing > 0}
          aria-label={t("ADD_DEVICE")}
          title={t("ADD_DEVICE")}
          className="border-2 border-gray-300 dark:border-gray-600 rounded-full w-10 h-10 text-2xl leading-none hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50"
        >
          +
        </button>
        </div>
      </div>
      {pairing > 0 && (
        <p role="status" className="mx-4 md:mx-6 mb-2 text-sm text-center text-green-500">
          {t("PAIRING_ACTIVE", { seconds: pairing })}
        </p>
      )}
      {!connected && !loading && (
        <p role="status" className="mx-4 md:mx-6 mb-2 text-sm text-center text-yellow-500">{t("CONNECTION_LOST")}</p>
      )}
      {error && <p role="alert" className="mx-4 md:mx-6 mb-2 text-sm text-center text-red-500">{error}</p>}
      {loading ? (
        <p className="p-8 text-center text-gray-500">{t("LOADING")}</p>
      ) : (
        layout === "bento" ? (
          <CDeviceBento
            devices={devices}
            onDeviceClick={(d) => setSelectedId(d.id)}
            onToggle={toggleDevice}
            onBrightness={setBrightness}
          />
        ) : (
          <CDeviceList
            devices={devices}
            onDeviceClick={(d) => setSelectedId(d.id)}
            onToggle={toggleDevice}
            onBrightness={setBrightness}
          />
        )
      )}
      <CNotice notice={notice} />
    </div>
  );
}
