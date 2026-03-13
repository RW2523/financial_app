import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { PageContent } from "../components/ui";
import {
  getInsightsHealthScore,
  getInsightsOverview,
  getInsightsTrends,
  getInsightsRecommendations,
  getInsightsAnomalies,
  getInsightsNarrative,
  getForecastMonth,
  getPredictiveAlerts,
} from "../api/client";
import { formatMoney } from "../lib/utils";

function formatRange(days: number) {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - days);
  return {
    start_str: start.toISOString().slice(0, 10),
    end_str: end.toISOString().slice(0, 10),
  };
}

export default function Insights() {
  const [health, setHealth] = useState<{ score: number; metrics?: Record<string, unknown> } | null>(null);
  const [overview, setOverview] = useState<Record<string, unknown> | null>(null);
  const [trends, setTrends] = useState<{ label: string; total_spend: number; transaction_count: number }[]>([]);
  const [recommendations, setRecommendations] = useState<{ title: string; suggestion: string }[]>([]);
  const [anomalies, setAnomalies] = useState<unknown[]>([]);
  const [narrative, setNarrative] = useState<string | null>(null);
  const [forecast, setForecast] = useState<Awaited<ReturnType<typeof getForecastMonth>> | null>(null);
  const [predictiveAlerts, setPredictiveAlerts] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [narrativeLoading, setNarrativeLoading] = useState(false);
  const [days, setDays] = useState(30);

  const { start_str, end_str } = formatRange(days);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [h, ov, tr, rec, anom, fc, pred] = await Promise.all([
          getInsightsHealthScore().catch(() => null),
          getInsightsOverview({ start_date: start_str, end_date: end_str }).catch(() => null),
          getInsightsTrends(6).then((r) => r.trends ?? []).catch(() => []),
          getInsightsRecommendations().then((r) => r.recommendations ?? []).catch(() => []),
          getInsightsAnomalies({ start_date: start_str, end_date: end_str }).then((r) => r.anomalies ?? []).catch(() => []),
          getForecastMonth().catch(() => null),
          getPredictiveAlerts().then((r) => (r.alerts ?? []).map((a) => a.message)).catch(() => []),
        ]);
        if (cancelled) return;
        setHealth(h);
        setOverview(ov);
        setTrends(tr);
        setRecommendations(rec);
        setAnomalies(anom);
        setForecast(fc);
        setPredictiveAlerts(pred);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [start_str, end_str]);

  const handleNarrative = async () => {
    setNarrativeLoading(true);
    setNarrative(null);
    try {
      const res = await getInsightsNarrative({ start_date: start_str, end_date: end_str });
      setNarrative(res.narrative ?? "No narrative generated.");
    } catch {
      setNarrative("Failed to generate narrative.");
    } finally {
      setNarrativeLoading(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Insights"
        subtitle="KPIs, trends, recommendations, and anomalies. Choose date range."
      />
      <PageContent loading={loading && !overview} loadingMessage="Loading insights…">
        <div className="space-y-6">
        <div className="flex gap-4 items-center">
          <label className="flex items-center gap-2 text-sm text-text-secondary">
            Last
            <select
              className="input-field w-24"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            >
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
            </select>
          </label>
        </div>

        {health && (
          <div className="card">
            <h3 className="font-medium text-text-primary mb-2">Budget health</h3>
            <p className="text-2xl font-semibold text-accent">{health.score} / 100</p>
            {health.metrics && (
              <pre className="mt-2 text-xs text-text-secondary overflow-x-auto">{JSON.stringify(health.metrics, null, 2)}</pre>
            )}
          </div>
        )}

        {overview && (
          <div className="card">
            <h3 className="font-medium text-text-primary mb-4">KPI cards</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div>
                <p className="text-text-secondary text-sm">Total spend</p>
                <p className="text-xl font-semibold text-text-primary">{formatMoney(Number(overview.total_spend ?? 0))}</p>
              </div>
              <div>
                <p className="text-text-secondary text-sm">Transactions</p>
                <p className="text-xl font-semibold text-text-primary">{String(overview.transaction_count ?? 0)}</p>
              </div>
              <div>
                <p className="text-text-secondary text-sm">Avg transaction</p>
                <p className="text-xl font-semibold text-text-primary">{formatMoney(Number(overview.average_transaction_amount ?? 0))}</p>
              </div>
              <div>
                <p className="text-text-secondary text-sm">Vs previous</p>
                <p className="text-xl font-semibold text-text-primary">{overview.spend_delta_percent != null ? `${Number(overview.spend_delta_percent)}%` : "—"}</p>
              </div>
              <div>
                <p className="text-text-secondary text-sm">Recurring burden</p>
                <p className="text-xl font-semibold text-text-primary">{overview.recurring_burden_percent != null ? `${Number(overview.recurring_burden_percent)}%` : "—"}</p>
              </div>
            </div>
            {overview.category_breakdown && Array.isArray(overview.category_breakdown) ? (
              <div className="mt-4">
                <h4 className="font-medium text-text-primary mb-2">Category breakdown</h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-text-secondary">
                        <th className="py-2 pr-4">Category</th>
                        <th className="py-2 pr-4 text-right">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(overview.category_breakdown as { category?: string; total?: number }[]).map((row, i) => (
                        <tr key={i} className="border-b border-border/50">
                          <td className="py-2 pr-4">{row.category ?? "—"}</td>
                          <td className="py-2 pr-4 text-right">{formatMoney(Number(row.total ?? 0))}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}
          </div>
        )}

        {trends.length > 0 && (
          <div className="card">
            <h3 className="font-medium text-text-primary mb-4">Trends (last 6 months)</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-text-secondary">
                    <th className="py-2 pr-4">Month</th>
                    <th className="py-2 pr-4 text-right">Total</th>
                    <th className="py-2 pr-4 text-right">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {trends.map((t, i) => (
                    <tr key={i} className="border-b border-border/50">
                      <td className="py-2 pr-4">{t.label}</td>
                      <td className="py-2 pr-4 text-right">{formatMoney(t.total_spend)}</td>
                      <td className="py-2 pr-4 text-right">{t.transaction_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {forecast && (
          <div className="card">
            <h3 className="font-medium text-text-primary mb-2">Month forecast</h3>
            <p className="text-text-secondary text-sm">
              Projected total: {forecast.projected_total != null ? formatMoney(forecast.projected_total) : "—"} ({forecast.days_elapsed ?? 0}/{forecast.days_in_month ?? 30} days)
            </p>
            {predictiveAlerts.length > 0 && (
              <ul className="mt-2 text-amber-400 text-sm space-y-1">
                {predictiveAlerts.map((m, i) => (
                  <li key={i}>{m}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {recommendations.length > 0 && (
          <div className="card">
            <h3 className="font-medium text-text-primary mb-4">Recommendations</h3>
            <ul className="space-y-3">
              {recommendations.map((r, i) => (
                <li key={i}>
                  <p className="font-medium text-text-primary">{r.title}</p>
                  <p className="text-text-secondary text-sm">{r.suggestion}</p>
                </li>
              ))}
            </ul>
          </div>
        )}

        {anomalies.length > 0 && (
          <div className="card">
            <h3 className="font-medium text-text-primary mb-4">Anomalous expenses</h3>
            <pre className="text-xs text-text-secondary overflow-x-auto">{JSON.stringify(anomalies, null, 2)}</pre>
          </div>
        )}

        <div className="card">
          <h3 className="font-medium text-text-primary mb-2">AI narrative</h3>
          <button className="btn-primary mb-3" onClick={handleNarrative} disabled={narrativeLoading}>
            {narrativeLoading ? "Generating…" : "Generate AI narrative"}
          </button>
          {narrative && <p className="text-text-secondary whitespace-pre-wrap text-sm">{narrative}</p>}
        </div>
        </div>
      </PageContent>
    </>
  );
}
