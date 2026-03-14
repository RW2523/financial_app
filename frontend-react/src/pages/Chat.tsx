import { useState, useRef, useEffect } from "react";
import { Send, Mic, Square } from "lucide-react";
import { chat, chatVoice, type ChatResponse } from "../api/client";

type Message = { role: "user" | "assistant"; content: string; transcript?: string };

const WELCOME = "Type or speak to add an expense (e.g. \"$50 on groceries yesterday\") or ask a question (e.g. \"How much did I spend on food last month?\").";

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([{ role: "assistant", content: WELCOME }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo(0, listRef.current.scrollHeight);
  }, [messages]);

  const append = (role: "user" | "assistant", content: string, transcript?: string) => {
    setMessages((prev) => [...prev, { role, content, transcript }]);
  };

  const handleResponse = (res: ChatResponse, userText: string) => {
    if (res.type === "expense_added") {
      append("assistant", res.message);
    } else {
      append("assistant", res.answer_text || "No answer.");
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    append("user", text);
    setLoading(true);
    try {
      const res = await chat(text);
      handleResponse(res, text);
    } catch (e) {
      append("assistant", e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: "audio/wav" });
        setLoading(true);
        chatVoice(blob)
          .then((res) => {
            const transcript = "transcript" in res ? (res as { transcript?: string }).transcript : undefined;
            append("user", transcript || "[Voice message]", transcript);
            handleResponse(res, transcript || "");
          })
          .catch((e) => append("assistant", e instanceof Error ? e.message : "Voice failed."))
          .finally(() => setLoading(false));
      };
      rec.start();
      mediaRecorderRef.current = rec;
      setRecording(true);
    } catch {
      append("assistant", "Microphone access denied or unavailable.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }
    setRecording(false);
  };

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto">
      <div className="border-b border-border bg-surface-elevated px-4 py-3">
        <h1 className="text-lg font-semibold text-text-primary">Chat</h1>
        <p className="text-sm text-text-secondary mt-0.5">Add expenses or ask questions. Type or use the mic.</p>
      </div>

      <div ref={listRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                m.role === "user"
                  ? "bg-accent text-white"
                  : "bg-surface-elevated border border-border text-text-primary"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.role === "user" && m.transcript !== undefined && m.transcript !== m.content && (
                <p className="text-xs opacity-80 mt-1 border-t border-white/20 pt-1">{m.transcript}</p>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface-elevated border border-border rounded-2xl px-4 py-2.5 text-sm text-text-secondary">
              …
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-border bg-surface-elevated p-3 flex gap-2">
        <input
          type="text"
          className="input-field flex-1"
          placeholder="Add expense or ask a question…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          disabled={loading}
          aria-label="Message"
        />
        {!recording ? (
          <button
            type="button"
            className="btn-secondary p-2.5"
            onClick={startRecording}
            disabled={loading}
            aria-label="Record voice"
          >
            <Mic className="h-5 w-5" />
          </button>
        ) : (
          <button
            type="button"
            className="btn-secondary p-2.5 border-red-500/50 text-red-400"
            onClick={stopRecording}
            aria-label="Stop recording"
          >
            <Square className="h-5 w-5" />
          </button>
        )}
        <button
          type="button"
          className="btn-primary p-2.5"
          onClick={handleSend}
          disabled={loading || !input.trim()}
          aria-label="Send"
        >
          <Send className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}
