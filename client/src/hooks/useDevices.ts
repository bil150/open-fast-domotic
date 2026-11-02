import { useCallback, useEffect, useRef, useState } from "react";
import { api, liveUrl } from "../api/client";
import { Device, LiveMessage } from "../api/types";

const RECONNECT_DELAY = 3000;

/** Apply one live message to the device list. Exported for tests. */
export function applyLiveMessage(devices: Device[], message: LiveMessage): Device[] {
  if (message.type === "state") {
    return devices.map((d) =>
      d.id === message.device_id
        ? {
            ...d,
            state: { ...d.state, ...(message.data.state ?? {}) },
            online: message.data.online === undefined ? d.online : message.data.online,
          }
        : d
    );
  }
  if (message.type === "button") {
    return devices.map((d) =>
      d.id === message.device_id
        ? {
            ...d,
            online: true,
            state: {
              ...d.state,
              last_button: { event: message.data.event ?? "", at: message.data.at ?? "" },
            },
          }
        : d
    );
  }
  return devices;
}

/** The device list, kept up to date by the server's WebSocket. */
export function useDevices() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const mounted = useRef(true);

  const reload = useCallback(async () => {
    try {
      const list = await api.devices.list();
      if (mounted.current) {
        setDevices(list);
        setError(null);
      }
    } catch (e) {
      if (mounted.current) setError((e as Error).message);
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, []);

  /** Replace one device with a fresher copy (e.g. the answer to a command). */
  const replace = useCallback((device: Device) => {
    setDevices((current) => current.map((d) => (d.id === device.id ? device : d)));
  }, []);

  useEffect(() => {
    mounted.current = true;
    reload();

    let socket: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      socket = new WebSocket(liveUrl());
      socket.onopen = () => {
        setConnected(true);
        reload(); // catch up on what happened while disconnected
      };
      socket.onmessage = (event) => {
        const message: LiveMessage = JSON.parse(event.data);
        if (message.type === "joined" || message.type === "left") {
          reload();
        } else {
          setDevices((current) => applyLiveMessage(current, message));
        }
      };
      socket.onclose = () => {
        setConnected(false);
        if (mounted.current) timer = setTimeout(connect, RECONNECT_DELAY);
      };
    };
    connect();

    return () => {
      mounted.current = false;
      if (timer) clearTimeout(timer);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, [reload]);

  return { devices, loading, error, connected, reload, replace };
}
