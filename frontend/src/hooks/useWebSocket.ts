import { useEffect, useRef, useState } from "react";

export function useWebSocket<T>(url: string, onMessage: (value: T) => void) {
  const [isUpdating, setIsUpdating] = useState(false);
  const attemptRef = useRef(0);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let timer: number | undefined;
    let closedManually = false;

    const connect = () => {
      ws = new WebSocket(url);
      ws.onmessage = (event) => {
        setIsUpdating(true);
        onMessage(JSON.parse(event.data) as T);
        window.setTimeout(() => setIsUpdating(false), 1000);
      };
      ws.onopen = () => {
        attemptRef.current = 0;
      };
      ws.onclose = () => {
        if (closedManually) return;
        const backoff = Math.min(30_000, 1000 * 2 ** attemptRef.current);
        attemptRef.current += 1;
        timer = window.setTimeout(connect, backoff);
      };
    };

    connect();
    return () => {
      closedManually = true;
      if (timer) window.clearTimeout(timer);
      ws?.close();
    };
  }, [onMessage, url]);

  return { isUpdating };
}
