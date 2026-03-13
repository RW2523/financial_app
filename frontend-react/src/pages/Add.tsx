import { useState } from "react";
import { Mic, Type } from "lucide-react";
import PageHeader from "../components/PageHeader";
import { ErrorMessage, SuccessMessage } from "../components/ui";
import { addTextExpense, addAudioExpense } from "../api/client";

export default function Add() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);

  const handleTextSubmit = async () => {
    if (!text.trim()) return;
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      await addTextExpense(text.trim());
      setSuccess("Expense added successfully.");
      setText("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add expense.");
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
        setAudioFile(new File([new Blob(chunks, { type: "audio/wav" })], "audio.wav", { type: "audio/wav" }));
      };
      rec.start();
      setMediaRecorder(rec);
      setRecording(true);
    } catch {
      setError("Microphone access denied or unavailable.");
    }
  };

  const stopRecording = () => {
    mediaRecorder?.stop();
    setMediaRecorder(null);
    setRecording(false);
  };

  const handleVoiceSubmit = async () => {
    if (!audioFile) return;
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      await addAudioExpense(audioFile);
      setSuccess("Expense added from voice.");
      setAudioFile(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add expense.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Add expense"
        subtitle="Use text or voice to log an expense. The AI will extract amount, category, and date."
      />
      <div className="p-6 max-w-4xl">
        <div className="grid md:grid-cols-2 gap-6">
          <div className="card">
            <div className="flex items-center gap-2 text-text-primary font-medium mb-3">
              <Type className="h-5 w-5 text-accent" aria-hidden />
              Text
            </div>
            <textarea
              className="input-field min-h-[120px] resize-y"
              placeholder="e.g. Spent $45 on groceries yesterday"
              value={text}
              onChange={(e) => setText(e.target.value)}
              aria-label="Expense description"
            />
            <button
              type="button"
              className="btn-primary mt-3"
              onClick={handleTextSubmit}
              disabled={loading || !text.trim()}
            >
              {loading ? "Processing…" : "Add from text"}
            </button>
          </div>

          <div className="card">
            <div className="flex items-center gap-2 text-text-primary font-medium mb-3">
              <Mic className="h-5 w-5 text-accent" aria-hidden />
              Voice
            </div>
            <p className="text-sm text-text-secondary mb-3">Click to record, then click again to stop.</p>
            {!recording ? (
              <button type="button" className="btn-primary" onClick={startRecording} disabled={loading}>
                Start recording
              </button>
            ) : (
              <button type="button" className="btn-secondary border-red-500/50 text-red-400" onClick={stopRecording}>
                Stop recording
              </button>
            )}
            {audioFile && (
              <div className="mt-3">
                <audio src={URL.createObjectURL(audioFile)} controls className="w-full" />
                <button
                  type="button"
                  className="btn-primary mt-2"
                  onClick={handleVoiceSubmit}
                  disabled={loading}
                >
                  {loading ? "Processing…" : "Add from voice"}
                </button>
              </div>
            )}
          </div>
        </div>

        {error && <div className="mt-4"><ErrorMessage message={error} /></div>}
        {success && <div className="mt-4"><SuccessMessage message={success} /></div>}
      </div>
    </>
  );
}
