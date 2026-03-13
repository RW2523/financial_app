import { useState } from "react";
import PageHeader from "../components/PageHeader";
import { ErrorMessage } from "../components/ui";
import { ask } from "../api/client";

export default function Ask() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ answer: string; filters_used?: unknown; supporting_data?: unknown } | null>(null);

  const handleAsk = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await ask(question.trim());
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Ask AI"
        subtitle="Ask questions in natural language. The AI uses your expense data to answer."
      />
      <div className="p-6 max-w-3xl">
        <div className="card">
          <textarea
            className="input-field min-h-[100px] resize-y"
            placeholder="e.g. How much did I spend on food last month?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            aria-label="Your question"
          />
          <button
            type="button"
            className="btn-primary mt-3"
            onClick={handleAsk}
            disabled={loading || !question.trim()}
          >
            {loading ? "Asking…" : "Ask"}
          </button>
        </div>

        {error && <div className="mt-4"><ErrorMessage message={error} /></div>}

        {result && (
          <div className="mt-6 space-y-4">
            <div className="card">
              <h3 className="font-medium text-text-primary mb-2">Answer</h3>
              <p className="text-text-secondary whitespace-pre-wrap">{result.answer}</p>
            </div>
            {result.filters_used != null && (
              <details className="card">
                <summary className="cursor-pointer font-medium text-text-secondary">Parsed filters</summary>
                <pre className="mt-2 text-xs text-text-secondary overflow-x-auto">{JSON.stringify(result.filters_used, null, 2)}</pre>
              </details>
            )}
            {result.supporting_data != null && (
              <details className="card">
                <summary className="cursor-pointer font-medium text-text-secondary">Supporting data</summary>
                <pre className="mt-2 text-xs text-text-secondary overflow-x-auto">{JSON.stringify(result.supporting_data, null, 2)}</pre>
              </details>
            )}
          </div>
        )}
      </div>
    </>
  );
}
