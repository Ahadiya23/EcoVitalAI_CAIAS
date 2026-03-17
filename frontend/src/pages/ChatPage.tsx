import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { useChat } from "../hooks/useChat";
import { useAppStore } from "../store/useAppStore";

export function ChatPage() {
  const user = useAppStore((s) => s.user);
  const userId = user?.id ?? "demo-user";
  const { messages, sendMessage, isStreaming, suggestions } = useChat(userId);
  const [input, setInput] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(true);

  return (
    <div className="flex h-[75vh] flex-col rounded-xl border bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      {showSuggestions && (
        <div className="mb-3 flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button key={s} className="rounded-full border px-3 py-1 text-xs" onClick={() => { setInput(s); setShowSuggestions(false); }}>
              {s}
            </button>
          ))}
        </div>
      )}
      <div className="flex-1 space-y-3 overflow-auto">
        {messages.map((m, i) => (
          <div key={i} className={`max-w-[80%] rounded-lg p-3 ${m.role === "user" ? "ml-auto bg-emerald-600 text-white" : "bg-slate-100 dark:bg-slate-800"}`}>
            {m.role === "assistant" ? <ReactMarkdown>{m.content}</ReactMarkdown> : m.content}
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <input className="flex-1 rounded border px-3 py-2" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask EcoVital AI..." />
        <button
          disabled={isStreaming || !input.trim()}
          className="rounded bg-emerald-600 px-4 py-2 text-white disabled:opacity-50"
          onClick={() => {
            sendMessage(input);
            setInput("");
            setShowSuggestions(false);
          }}
        >
          {isStreaming ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
