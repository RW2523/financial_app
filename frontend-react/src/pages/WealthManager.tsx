import { useState, useEffect } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import PageHeader from "../components/PageHeader";
import { MetricCard, PageContent } from "../components/ui";
import { getPortfolioManagerView } from "../api/client";
import { formatMoney } from "../lib/utils";

const SECTOR_COLORS: Record<string, string> = {
  Technology: "#3b82f6",
  Financials: "#22c55e",
  Healthcare: "#a855f7",
  Energy: "#eab308",
  "Consumer Defensive": "#f97316",
  "Consumer Cyclical": "#ec4899",
  Communication: "#06b6d4",
  Other: "#64748b",
};

const DEFAULT_COLOR = "#94a3b8";

export default function WealthManager() {
  const [data, setData] = useState<Awaited<ReturnType<typeof getPortfolioManagerView>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getPortfolioManagerView()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load."))
      .finally(() => setLoading(false));
  }, []);

  const sectorData = data?.allocation_by_sector
    ? Object.entries(data.allocation_by_sector)
        .filter(([, pct]) => pct > 0)
        .map(([name, value]) => ({ name, value }))
    : [];

  return (
    <>
      <PageHeader
        title="Portfolio Intelligence"
        subtitle="Allocation by sector, diversification score, and stocks that fit your portfolio. Rebalancing suggestions to add missing sectors."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading portfolio manager…">
        {!loading && data && (
          <div className="space-y-8">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <MetricCard
                label="Portfolio value"
                value={formatMoney(data.total_portfolio_value)}
                accent
              />
              <MetricCard
                label="Diversification score"
                value={`${data.diversification_score}/100`}
                sub={data.diversification_score >= 60 ? "Good spread" : "Consider diversifying"}
              />
              <MetricCard label="Holdings" value={data.your_holdings_count} sub={data.sectors_held?.join(", ") || "—"} />
            </div>

            {data.diversification_explanation && (
              <div className="card">
                <h3 className="font-medium text-text-primary mb-2">Diversification score explanation</h3>
                <p className="text-sm text-text-secondary">{data.diversification_explanation}</p>
              </div>
            )}
            {data.sector_gaps && data.sector_gaps.length > 0 && (
              <div className="card">
                <h3 className="font-medium text-text-primary mb-2">Sector gap analysis</h3>
                <p className="text-sm text-text-secondary mb-2">Sectors not currently in your portfolio:</p>
                <div className="flex flex-wrap gap-2">
                  {data.sector_gaps.map((s) => (
                    <span key={s} className="px-2 py-1 rounded bg-amber-500/20 text-amber-300 text-sm">{s}</span>
                  ))}
                </div>
              </div>
            )}
            {data.rebalancing_impact_preview && (
              <div className="card bg-accent/10 border border-accent/30">
                <h3 className="font-medium text-text-primary mb-2">Rebalancing impact preview</h3>
                <p className="text-sm text-text-secondary">{data.rebalancing_impact_preview.message}</p>
              </div>
            )}

            {sectorData.length > 0 && (
              <div className="card">
                <h3 className="font-medium text-text-primary mb-4">Allocation by sector</h3>
                <div className="flex flex-col sm:flex-row gap-6 items-start">
                  <div style={{ width: 280, height: 280 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={sectorData}
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={100}
                          paddingAngle={2}
                          dataKey="value"
                          nameKey="name"
                          label={({ name, value }) => `${name} ${value}%`}
                        >
                          {sectorData.map((entry) => (
                            <Cell
                              key={entry.name}
                              fill={SECTOR_COLORS[entry.name] || DEFAULT_COLOR}
                            />
                          ))}
                        </Pie>
                        <Tooltip formatter={(v: unknown) => `${v}%`} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <ul className="text-sm text-text-secondary space-y-1">
                    {Object.entries(data.allocation_by_sector)
                      .filter(([, pct]) => pct > 0)
                      .sort((a, b) => b[1] - a[1])
                      .map(([sector, pct]) => (
                        <li key={sector}>
                          <span className="inline-block w-3 h-3 rounded-full mr-2 align-middle" style={{ backgroundColor: SECTOR_COLORS[sector] || DEFAULT_COLOR }} />
                          {sector}: {pct}%
                        </li>
                      ))}
                  </ul>
                </div>
              </div>
            )}

            <div className="card">
              <h3 className="font-medium text-text-primary mb-2">Stocks that work for you</h3>
              <p className="text-sm text-text-secondary mb-4">
                Picks to improve diversification and income, based on your current portfolio.
              </p>
              {!data.stocks_that_work_for_you?.length ? (
                <p className="text-text-secondary text-sm">Add holdings in Investments to get personalized picks.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-text-secondary border-b border-border">
                        <th className="pb-2 pr-4">Ticker</th>
                        <th className="pb-2 pr-4">Name</th>
                        <th className="pb-2 pr-4">Sector</th>
                        <th className="pb-2 pr-4">Price</th>
                        <th className="pb-2 pr-4">Div yield</th>
                        <th className="pb-2 pr-4">Why for you</th>
                      </tr>
                    </thead>
                    <tbody className="text-text-primary">
                      {data.stocks_that_work_for_you.map((s) => (
                        <tr key={s.ticker} className="border-b border-border/50">
                          <td className="py-2 pr-4 font-medium">{s.ticker}</td>
                          <td className="py-2 pr-4">{s.stock_name ?? "—"}</td>
                          <td className="py-2 pr-4">{s.sector ?? "—"}</td>
                          <td className="py-2 pr-4">{s.current_price != null ? formatMoney(s.current_price) : "—"}</td>
                          <td className="py-2 pr-4">{s.dividend_yield != null ? `${s.dividend_yield}%` : "—"}</td>
                          <td className="py-2 pr-4 text-text-secondary">{s.why_for_you}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {data.rebalancing_suggestions?.length > 0 && (
              <div className="card">
                <h3 className="font-medium text-text-primary mb-2">Rebalancing</h3>
                <p className="text-sm text-text-secondary mb-4">Sectors you don’t hold yet — consider adding exposure.</p>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {data.rebalancing_suggestions.map((r) => (
                    <div
                      key={r.sector}
                      className="p-4 rounded-lg bg-surface-muted border border-border"
                    >
                      <p className="font-medium text-text-primary">{r.sector}</p>
                      <p className="text-sm text-text-secondary mt-1">{r.suggestion}</p>
                      <p className="text-sm mt-2">
                        <span className="text-accent">{r.top_pick}</span> — {r.top_pick_name}
                        {r.price != null && ` · ${formatMoney(r.price)}`}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </PageContent>
    </>
  );
}
