import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getWealthOverview } from "../api/client";
import { formatMoney } from "../lib/utils";
import { WEALTH_ROUTES } from "../wealth";

export default function WealthHubSummaryBar() {
  const [data, setData] = useState<Awaited<ReturnType<typeof getWealthOverview>> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getWealthOverview()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return (
      <div className="border-b border-border bg-surface-muted/50 px-4 py-2 flex flex-wrap gap-4 items-center text-sm text-text-muted">
        Loading…
      </div>
    );
  }

  const strip = data.summary_strip || {};
  const score = data.wealth_score ?? strip.wealth_score;

  return (
    <div className="border-b border-border bg-surface-muted/50 px-4 py-2 flex flex-wrap gap-x-6 gap-y-1 items-center text-sm">
      <span className="text-text-muted">Income:</span>
      <span className="text-text-primary font-medium">{formatMoney(strip.net_income_this_month ?? 0)}</span>
      <span className="text-text-muted">Expenses:</span>
      <span className="text-text-primary">{formatMoney(strip.total_expenses_this_month ?? 0)}</span>
      <span className="text-text-muted">Free cash:</span>
      <span className="text-text-primary">{formatMoney(strip.free_cash_this_month ?? 0)}</span>
      <span className="text-text-muted">Invested:</span>
      <span className="text-text-primary">{formatMoney(strip.invested_this_month ?? 0)}</span>
      <span className="text-text-muted">Portfolio:</span>
      <Link to={WEALTH_ROUTES.portfolio} className="text-accent hover:underline font-medium">
        {formatMoney(strip.portfolio_value ?? 0)}
      </Link>
      {score != null && (
        <>
          <span className="text-text-muted">Wealth Score:</span>
          <span className={score >= 60 ? "text-green-400 font-medium" : score >= 40 ? "text-amber-400 font-medium" : "text-red-400 font-medium"}>
            {score}/100
          </span>
        </>
      )}
    </div>
  );
}
