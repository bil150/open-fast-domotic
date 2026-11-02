import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import { Device } from "../../api/types";
import { DeviceIcon } from "../subcomponents/display/DeviceIcon";

export interface CDeviceHeaderProps {
  device: Device;
  onListClick: () => void;
  onDeviceChange: (device: Device) => void;
  onError: (message: string) => void;
}

/** Back button, device name (click to rename) and type icon. */
export function CDeviceHeader(props: CDeviceHeaderProps) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(props.device.name);

  async function save() {
    setEditing(false);
    if (name.trim() === props.device.name) return;
    try {
      props.onDeviceChange(await api.devices.rename(props.device.id, name.trim() || null));
    } catch (e) {
      props.onError((e as Error).message);
    }
  }

  return (
    <div className="flex justify-between items-center py-1 px-4 md:px-6 gap-2 min-h-[4rem]">
      <button
        aria-label={t("BACK")}
        onClick={props.onListClick}
        className="border-2 border-gray-300 dark:border-gray-600 rounded-full p-2 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors duration-300"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6">
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0ZM3.75 12h.007v.008H3.75V12Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm-.375 5.25h.007v.008H3.75v-.008Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
        </svg>
      </button>
      {editing ? (
        <input
          autoFocus
          aria-label={t("RENAME")}
          value={name}
          maxLength={60}
          onChange={(e) => setName(e.target.value)}
          onBlur={save}
          onKeyDown={(e) => e.key === "Enter" && save()}
          className="text-xl bg-transparent border-b-2 border-gray-400 text-center min-w-0 flex-grow"
        />
      ) : (
        <h2
          title={t("RENAME")}
          onClick={() => {
            setName(props.device.name);
            setEditing(true);
          }}
          className="text-2xl truncate cursor-text"
        >
          {props.device.name}
        </h2>
      )}
      <div className="border-2 border-gray-300 dark:border-gray-600 rounded-full p-2">
        <DeviceIcon type={props.device.type} />
      </div>
    </div>
  );
}
