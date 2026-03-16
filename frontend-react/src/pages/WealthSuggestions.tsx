import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { PageContent } from "../components/ui";
import { getSuggestions } from "../api/client";
import type { Suggestion } from "../api/client";
import { currentYear, currentMonth, WealthMonthYearPicker } from "../wealth";

const SEVERITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

function SuggestionCard({ s }: { s: Suggestion }) {
  const isHigh = s.severity === "high";
  const isMedium = s.severity === "medium";
  const bg = isHigh
    ? "bg-red-500/10 border-red-500/30"
    : isMedium
      ? "bg-amber-500/10 border-amber-500/30"
      : "bg-blue-500/10 border-blue-500/30";
  const titleColor = isHigh ? "text-red-300" : isMedium ? "text-amber-300" : "text-blue-300";

  const content = (
    <>
      <p className={`font-medium ${titleColor}`}>{s.title}</p>
      <p className="text-sm text-text-secondary mt-1">{s.message}</p>
      {s.why_this_matters && (
        <p className="text-sm text-text-muted mt-2"><strong>Why this matters:</strong> {s.why_this_matters}</p>
      )}
      <p className="text-xs text-text-muted mt-2">Metric: {s.metric} = {s.value}</p>
    </>
  );

  if (s.destination) {
    return (
      <Link to={s.destination} className={`card border ${bg} block hover:opacity-90 transition-opacity`}>
        {content}
        <p className="text-xs text-accent mt-2">Go to destination →</p>
      </Link>
    );
  }
  return <div className={`card border ${bg}`}>{content}</div>;
}

export default function WealthSuggestions() {
  const [year, setYear] = useState(currentYear);
  const [month, setMonth] = useState(currentMonth);
  const [data, setData] = useState<Awaited<ReturnType<typeof getSuggestions>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getSuggestions(year, month);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load suggestions.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [year, month]);

  return (
    <>
      <PageHeader
        title="Suggestions"
        subtitle="Actionable tips from your data only: expense ratio, concentration, free cash, and savings. No generic advice."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading suggestions…">
        {!loading && data && (
          <div className="space-y-6">
            <WealthMonthYearPicker
              year={year}
              month={month}
              onYearChange={setYear}
              onMonthChange={setMonth}
            />

            {data.suggestions.length === 0 ? (
              <div className="card bg-green-500/10 border border-green-500/30">
                <p className="font-medium text-green-300">No suggestions</p>
                <p className="text-sm text-text-secondary mt-1">Metrics look healthy for this month.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {[...data.suggestions]
                  .sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 2) - (SEVERITY_ORDER[b.severity] ?? 2))
                  .map((s) => (
                    <SuggestionCard key={s.id} s={s} />
                  ))}
              </div>
            )}
          </div>
        )}
      </PageContent>
    </>
  );
}
