import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import { Device } from "../../api/types";
import { CConfirmDialog } from "../subcomponents/display/CConfirmDialog";
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
  const [confirming, setConfirming] = useState(false);

  async function save() {
    setEditing(false);
    if (name.trim() === props.device.name) return;
    try {
      props.onDeviceChange(await api.devices.rename(props.device.id, name.trim() || null));
    } catch (e) {
      props.onError((e as Error).message);
    }
  }

  async function remove() {
    setConfirming(false);
    try {
      await api.devices.remove(props.device.id);
      props.onListClick(); // the list drops it by itself (live update)
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
      <div className="flex items-center gap-2">
        <button
          aria-label={t("REMOVE_DEVICE")}
          title={t("REMOVE_DEVICE")}
          onClick={() => setConfirming(true)}
          className="rounded-full p-2 text-gray-400 dark:text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-300"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-5">
            <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
          </svg>
        </button>
        <div className="border-2 border-gray-300 dark:border-gray-600 rounded-full p-2">
          <DeviceIcon type={props.device.type} />
        </div>
      </div>
      {confirming && (
        <CConfirmDialog
          title={t("CONFIRM_REMOVE_DEVICE", { name: props.device.name })}
          message={t("REMOVE_DEVICE_INFO")}
          confirmLabel={t("DELETE")}
          onConfirm={remove}
          onCancel={() => setConfirming(false)}
        />
      )}
    </div>
  );
}
