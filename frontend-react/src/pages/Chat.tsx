import { useState, useRef, useEffect } from "react";
import { Send, Mic, Square, Bot, User, FileImage } from "lucide-react";
import { chat, chatVoice, addDocumentExpenses, type ChatResponse } from "../api/client";

type Message = { role: "user" | "assistant"; content: string; transcript?: string };

const WELCOME =
  "I'm your **SelavAI** assistant — I can do almost everything in the app from here.\n\n• **Expenses** — Add by text (\"$50 groceries yesterday\"), voice, or upload PDFs/images\n• **Spending** — \"Summary for last week\", \"Break down by category\", \"Last two days\"\n• **Limits** — \"Set food limit to 500\", \"Show my limits\", \"Remove transport limit\"\n• **Goals** — \"My goals\", \"Add goal save 5000 by 2026\"\n• **Affordability** — \"Can I afford 100 for dinner?\"\n• **Forecast & alerts** — \"Forecast\", \"Alerts\"\n• **More** — \"Sync Gmail\", \"Add sample data\", \"Help\"\n\nType or tap a suggestion below.";
const QUICK_ACTIONS = [
  "Help",
  "Summary for last week",
  "Show my limits",
  "Can I afford 50 for lunch?",
  "Forecast",
  "My goals",
  "Add sample data",
];

/** Render **bold** and newlines in assistant text */
function MessageContent({ text }: { text: string }) {
  const parts: React.ReactNode[] = [];
  let key = 0;
  const segments = text.split(/(\*\*[^*]+\*\*)/g);
  segments.forEach((seg) => {
    if (seg.startsWith("**") && seg.endsWith("**")) {
      parts.push(<strong key={key++}>{seg.slice(2, -2)}</strong>);
    } else {
      parts.push(seg);
    }
  });
  return <p className="whitespace-pre-wrap">{parts}</p>;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([{ role: "assistant", content: WELCOME }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo(0, listRef.current.scrollHeight);
  }, [messages]);

  const append = (role: "user" | "assistant", content: string, transcript?: string) => {
    setMessages((prev) => [...prev, { role, content, transcript }]);
  };

  const handleResponse = (res: ChatResponse, _userText: string) => {
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
      const history = messages
        .filter((m) => m.role === "user" || m.role === "assistant")
        .slice(-10)
        .map((m) => ({ role: m.role, content: m.content }));
      const res = await chat(text, history);
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

  const sendQuickAction = (text: string) => {
    if (!text.trim() || loading) return;
    setInput("");
    append("user", text);
    setLoading(true);
    const history = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .slice(-10)
      .map((m) => ({ role: m.role, content: m.content }));
    chat(text, history)
      .then((res) => handleResponse(res, text))
      .catch((e) => append("assistant", e instanceof Error ? e.message : "Something went wrong."))
      .finally(() => setLoading(false));
  };

  const handleDocumentUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList?.length || loading) return;
    const files = Array.from(fileList);
    const message = input.trim() || "These are my expenses";
    setInput("");
    append("user", `Uploaded ${files.length} file(s): ${files.map((f) => f.name).join(", ")}${message !== "These are my expenses" ? ` — "${message}"` : ""}`);
    e.target.value = "";
    setLoading(true);
    try {
      const res = await addDocumentExpenses(files, message);
      const reply =
        res.added > 0
          ? `**Added ${res.added} expense(s)** from your document(s).\n${res.expenses.slice(0, 5).map((ex) => `• ${ex.date} · ${ex.category} · ${ex.currency} ${ex.amount}`).join("\n")}${res.expenses.length > 5 ? `\n… and ${res.expenses.length - 5} more` : ""}`
          : res.message;
      append("assistant", reply);
    } catch (err) {
      append("assistant", err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto">
      <div className="border-b border-border bg-surface-elevated px-4 py-3">
        <h1 className="text-lg font-semibold text-text-primary">Chat</h1>
        <p className="text-sm text-text-secondary mt-0.5">
          Converse with SelavAI: add expenses, ask for summaries, and follow up with questions.
        </p>
      </div>

      <div ref={listRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 1 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {QUICK_ACTIONS.map((label) => (
              <button
                key={label}
                type="button"
                className="px-3 py-1.5 rounded-full text-sm bg-surface-muted border border-border text-text-secondary hover:bg-accent/10 hover:text-accent hover:border-accent/30 transition-colors"
                onClick={() => sendQuickAction(label)}
                disabled={loading}
              >
                {label}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex gap-2 ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {m.role === "assistant" && (
              <div className="shrink-0 w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center">
                <Bot className="w-4 h-4 text-accent" />
              </div>
            )}
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                m.role === "user"
                  ? "bg-accent text-white"
                  : "bg-surface-elevated border border-border text-text-primary"
              }`}
            >
              {m.role === "assistant" ? (
                <MessageContent text={m.content} />
              ) : (
                <>
                  <p className="whitespace-pre-wrap">{m.content}</p>
                  {m.transcript !== undefined && m.transcript !== m.content && (
                    <p className="text-xs opacity-80 mt-1 border-t border-white/20 pt-1">{m.transcript}</p>
                  )}
                </>
              )}
            </div>
            {m.role === "user" && (
              <div className="shrink-0 w-8 h-8 rounded-lg bg-accent/30 flex items-center justify-center">
                <User className="w-4 h-4 text-accent" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex justify-start gap-2">
            <div className="shrink-0 w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center">
              <Bot className="w-4 h-4 text-accent animate-pulse" />
            </div>
            <div className="bg-surface-elevated border border-border rounded-2xl px-4 py-2.5 text-sm text-text-secondary">
              …
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-border bg-surface-elevated p-3 flex gap-2 items-center">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.webp"
          multiple
          className="hidden"
          aria-label="Upload PDF or images"
          onChange={handleDocumentUpload}
        />
        <button
          type="button"
          className="btn-secondary p-2.5"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          aria-label="Upload PDF or images"
          title="Upload receipts (PDF or images)"
        >
          <FileImage className="h-5 w-5" />
        </button>
        <input
          type="text"
          className="input-field flex-1"
          placeholder="Add expense, ask a question, or upload PDF/images…"
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
