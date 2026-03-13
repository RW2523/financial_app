import { useState, useEffect } from "react";
import { Download } from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import PageHeader from "../components/PageHeader";
import { EmptyState, MetricCard, PageContent } from "../components/ui";
import { getExpenses, getInsightsHealthScore, type Expense } from "../api/client";
import { formatMoney } from "../lib/utils";

function byCategory(expenses: Expense[]): Record<string, number> {
  const map: Record<string, number> = {};
  for (const e of expenses) {
    const cat = e.category || "other";
    map[cat] = (map[cat] || 0) + Number(e.amount);
  }
  return map;
}

function byDate(expenses: Expense[]): { date: string; amount: number; total: number }[] {
  const map: Record<string, number> = {};
  for (const e of expenses) {
    const d = e.date?.slice(0, 10) ?? "";
    if (d) map[d] = (map[d] || 0) + Number(e.amount);
  }
  const entries = Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
  let running = 0;
  return entries.map(([date, amount]) => {
    running += amount;
    return { date, amount, total: running };
  });
}

function byMonth(expenses: Expense[]): { month: string; amount: number; count: number }[] {
  const map: Record<string, { amount: number; count: number }> = {};
  for (const e of expenses) {
    const d = e.date?.slice(0, 7) ?? "";
    if (!d) continue;
    if (!map[d]) map[d] = { amount: 0, count: 0 };
    map[d].amount += Number(e.amount);
    map[d].count += 1;
  }
  return Object.entries(map)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, v]) => ({ month, amount: v.amount, count: v.count }));
}

function downloadCSV(expenses: Expense[]) {
  const headers = ["date", "category", "amount", "currency", "raw_text"];
  const rows = expenses.map((e) =>
    headers.map((h) => {
      const v = (e as unknown as Record<string, unknown>)[h];
      const s = v == null ? "" : String(v);
      return s.includes(",") ? `"${s.replace(/"/g, '""')}"` : s;
    }).join(",")
  );
  const csv = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "expenses_export.csv";
  a.click();
  URL.revokeObjectURL(url);
}

const CHART_COLORS = [
  "#238636", // accent
  "#2ea043",
  "#3fb950",
  "#56d364",
  "#7ee787",
  "#9be9a8",
  "#3b82f6",
  "#60a5fa",
  "#8b5cf6",
  "#a78bfa",
];

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { value: number; name?: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-surface-elevated px-3 py-2 shadow-lg">
      {label && <p className="text-text-secondary text-xs mb-1">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} className="text-text-primary text-sm font-medium">
          {formatMoney(Number(p.value))}
        </p>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [healthScore, setHealthScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [exp, health] = await Promise.all([
          getExpenses(),
          getInsightsHealthScore().catch(() => null),
        ]);
        if (cancelled) return;
        const list = Array.isArray(exp) ? exp : [];
        setExpenses(list);
        if (health) setHealthScore(health.score);
        const dates = list.map((e) => e.date?.slice(0, 10)).filter(Boolean) as string[];
        if (dates.length) {
          const sorted = [...new Set(dates)].sort();
          setFrom(sorted[0]);
          setTo(sorted[sorted.length - 1]);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const filtered = expenses.filter((e) => {
    const d = e.date?.slice(0, 10);
    if (!d) return false;
    if (from && d < from) return false;
    if (to && d > to) return false;
    return true;
  });

  const total = filtered.reduce((s, e) => s + Number(e.amount), 0);
  const byCat = byCategory(filtered);
  const dailyData = byDate(filtered);
  const monthlyData = byMonth(filtered);
  const topCategory = Object.entries(byCat).sort((a, b) => b[1] - a[1])[0];

  const pieData = Object.entries(byCat)
    .sort((a, b) => b[1] - a[1])
    .map(([name, value], i) => ({ name, value, color: CHART_COLORS[i % CHART_COLORS.length] }));

  const barData = Object.entries(byCat)
    .sort((a, b) => b[1] - a[1])
    .map(([name, amount]) => ({ name, amount }));

  return (
    <>
      <PageHeader
        title="BI Dashboard"
        subtitle="Spending overview, interactive charts, and export for Power BI or Excel."
      />
      <PageContent loading={loading} error={error}>
        {!loading && (
          <>
            <div className="card flex flex-wrap gap-4 mb-6">
              <label className="flex flex-col gap-1">
                <span className="text-sm text-text-secondary">From</span>
                <input
                  type="date"
                  className="input-field w-40"
                  value={from}
                  onChange={(e) => setFrom(e.target.value)}
                  aria-label="From date"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-sm text-text-secondary">To</span>
                <input
                  type="date"
                  className="input-field w-40"
                  value={to}
                  onChange={(e) => setTo(e.target.value)}
                  aria-label="To date"
                />
              </label>
              {filtered.length > 0 && (
                <div className="flex items-end">
                  <button
                    type="button"
                    className="btn-secondary flex items-center gap-2"
                    onClick={() => downloadCSV(filtered)}
                  >
                    <Download className="h-4 w-4" aria-hidden />
                    Download CSV
                  </button>
                </div>
              )}
            </div>

            {filtered.length === 0 ? (
              <EmptyState message="No expenses in this date range. Adjust dates or add expenses in Add." />
            ) : (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  {healthScore != null && (
                    <MetricCard label="Budget health" value={`${healthScore} / 100`} accent />
                  )}
                  <MetricCard label="Total spend" value={formatMoney(total)} />
                  <MetricCard label="Transactions" value={filtered.length} />
                  {topCategory && (
                    <MetricCard
                      label="Top category"
                      value={`${topCategory[0]} (${formatMoney(topCategory[1])})`}
                    />
                  )}
                </div>

                {/* Spending over time (area chart) */}
                {dailyData.length > 0 && (
                  <div className="card mb-6">
                    <h3 className="font-medium text-text-primary mb-4">Spending over time</h3>
                    <div className="h-72 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={dailyData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                          <defs>
                            <linearGradient id="fillAmount" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#238636" stopOpacity={0.4} />
                              <stop offset="100%" stopColor="#238636" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#30363d" opacity={0.5} />
                          <XAxis
                            dataKey="date"
                            stroke="#8b949e"
                            tick={{ fill: "#8b949e", fontSize: 12 }}
                            tickFormatter={(v) => v.slice(5)}
                          />
                          <YAxis
                            stroke="#8b949e"
                            tick={{ fill: "#8b949e", fontSize: 12 }}
                            tickFormatter={(v) => `$${v}`}
                          />
                          <Tooltip content={<ChartTooltip />} />
                          <Area
                            type="monotone"
                            dataKey="amount"
                            name="Spend"
                            stroke="#238636"
                            strokeWidth={2}
                            fill="url(#fillAmount)"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                {/* Row: Category bar chart + Pie chart */}
                <div className="grid md:grid-cols-2 gap-6 mb-6">
                  {barData.length > 0 && (
                    <div className="card">
                      <h3 className="font-medium text-text-primary mb-4">Spending by category</h3>
                      <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={barData}
                            layout="vertical"
                            margin={{ top: 5, right: 20, left: 60, bottom: 5 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="#30363d" opacity={0.5} />
                            <XAxis type="number" stroke="#8b949e" tick={{ fill: "#8b949e", fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                            <YAxis type="category" dataKey="name" stroke="#8b949e" tick={{ fill: "#8b949e", fontSize: 12 }} width={55} />
                            <Tooltip content={<ChartTooltip />} />
                            <Bar dataKey="amount" name="Amount" fill="#238636" radius={[0, 4, 4, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                  {pieData.length > 0 && (
                    <div className="card">
                      <h3 className="font-medium text-text-primary mb-4">Share by category</h3>
                      <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={pieData}
                              dataKey="value"
                              nameKey="name"
                              cx="50%"
                              cy="50%"
                              outerRadius="70%"
                              innerRadius="45%"
                              paddingAngle={2}
                              label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                              labelLine={{ stroke: "#8b949e" }}
                            >
                              {pieData.map((entry, i) => (
                                <Cell key={i} fill={entry.color} stroke="#161b22" strokeWidth={2} />
                              ))}
                            </Pie>
                            <Tooltip
                              formatter={(value) => [formatMoney(Number(value)), "Amount"]}
                              contentStyle={{ backgroundColor: "#161b22", border: "1px solid #30363d", borderRadius: "8px" }}
                            />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                </div>

                {/* Monthly comparison */}
                {monthlyData.length > 0 && (
                  <div className="card">
                    <h3 className="font-medium text-text-primary mb-4">Monthly total spending</h3>
                    <div className="h-72 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={monthlyData} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#30363d" opacity={0.5} />
                          <XAxis
                            dataKey="month"
                            stroke="#8b949e"
                            tick={{ fill: "#8b949e", fontSize: 12 }}
                          />
                          <YAxis
                            stroke="#8b949e"
                            tick={{ fill: "#8b949e", fontSize: 12 }}
                            tickFormatter={(v) => `$${v}`}
                          />
                          <Tooltip content={<ChartTooltip />} />
                          <Bar dataKey="amount" name="Total" fill="#238636" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </PageContent>
    </>
  );
}
