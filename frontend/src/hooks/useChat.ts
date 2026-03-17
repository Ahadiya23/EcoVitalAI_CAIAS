import { useEffect, useMemo, useRef, useState } from "react";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export function useChat(userId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const streamRef = useRef<EventSource | null>(null);

  const sendMessage = (text: string) => {
    setMessages((prev) => [...prev, { role: "user", content: text }, { role: "assistant", content: "" }]);
    setIsStreaming(true);
    const source = new EventSource(
      `${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/api/chat/stream?user_id=${encodeURIComponent(userId)}&message=${encodeURIComponent(text)}`
    );
    streamRef.current = source;
    source.addEventListener("token", (event) => {
      const token = (event as MessageEvent).data;
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          ...next[next.length - 1],
          content: `${next[next.length - 1].content}${token}`
        };
        return next;
      });
    });
    source.addEventListener("done", () => {
      setIsStreaming(false);
      source.close();
    });
    source.onerror = () => {
      setIsStreaming(false);
      source.close();
    };
  };

  useEffect(() => () => streamRef.current?.close(), []);

  const suggestions = useMemo(
    () => [
      "Why is my risk high today?",
      "Is it safe to exercise outside right now?",
      "What should I avoid this evening?",
      "How does PM2.5 affect my asthma?"
    ],
    []
  );

  return { messages, sendMessage, isStreaming, suggestions };
}
