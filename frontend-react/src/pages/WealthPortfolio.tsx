import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import PageHeader from "../components/PageHeader";
import { EmptyState, MetricCard, PageContent } from "../components/ui";
import {
  getPortfolioSummary,
  getStockDetails,
  checkStockAffordability,
  searchStocks,
  getDiversificationSuggestions,
  addWatchlistItem,
  getSuggestions,
  type StockDetails as StockDetailsType,
  type DiversificationSuggestion,
} from "../api/client";
import { formatMoney } from "../lib/utils";
import { WEALTH_ROUTES } from "../wealth";

const PORTFOLIO_SUGGESTIONS_TOP_N = 2;

const CHART_COLORS = ["#238636", "#2ea043", "#3fb950", "#56d364", "#7ee787"];

export default function WealthPortfolio() {
  const [data, setData] = useState<Awaited<ReturnType<typeof getPortfolioSummary>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tickerLookup, setTickerLookup] = useState("AAPL");
  const [stockDetails, setStockDetails] = useState<Awaited<ReturnType<typeof getStockDetails>> | null>(null);
  const [affQty, setAffQty] = useState(10);
  const [affPrice, setAffPrice] = useState(150);
  const [affResult, setAffResult] = useState<Awaited<ReturnType<typeof checkStockAffordability>> | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<StockDetailsType[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [diversification, setDiversification] = useState<Awaited<ReturnType<typeof getDiversificationSuggestions>> | null>(null);
  const [watchlistAdded, setWatchlistAdded] = useState<Set<string>>(new Set());
  const [portfolioSuggestions, setPortfolioSuggestions] = useState<Awaited<ReturnType<typeof getSuggestions>>["suggestions"]>([]);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const summary = await getPortfolioSummary();
      setData(summary);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load portfolio.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!data) return;
    Promise.all([
      getDiversificationSuggestions().then(setDiversification).catch(() => setDiversification(null)),
      getSuggestions().then((r) => setPortfolioSuggestions(r.suggestions?.slice(0, PORTFOLIO_SUGGESTIONS_TOP_N) ?? [])),
    ]);
  }, [data]);

  const handleSearchStocks = async () => {
    setSearchLoading(true);
    setSearchResults([]);
    try {
      const list = await searchStocks(searchQuery.trim());
      setSearchResults(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed.");
    } finally {
      setSearchLoading(false);
    }
  };

  const useTickerForLookup = (ticker: string, price?: number) => {
    setTickerLookup(ticker);
    if (price != null) setAffPrice(price);
    setStockDetails(null);
    setAffResult(null);
  };

  const handleStockLookup = async () => {
    setStockDetails(null);
    try {
      const d = await getStockDetails(tickerLookup.trim());
      setStockDetails(d);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Stock lookup failed.");
    }
  };

  const handleAffordability = async () => {
    setAffResult(null);
    try {
      const r = await checkStockAffordability({
        ticker: tickerLookup.trim().toUpperCase(),
        quantity: affQty,
        price_per_share: affPrice,
      });
      setAffResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Affordability check failed.");
    }
  };

  const handleAddToWatchlist = async (ticker: string, stock_name?: string | null, sector?: string | null, current_price?: number | null) => {
    const key = ticker.toUpperCase();
    if (watchlistAdded.has(key)) return;
    try {
      await addWatchlistItem({
        ticker: key,
        stock_name: stock_name || undefined,
        sector: sector || undefined,
        current_price: current_price ?? undefined,
      });
      setWatchlistAdded((prev) => new Set(prev).add(key));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add to watchlist.");
    }
  };

  return (
    <>
      <PageHeader
        title="Portfolio"
        subtitle="Holdings, allocation, performance, and stock discovery. Check affordability and add to watchlist."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading portfolio…">
        {!loading && data && (
          <div className="space-y-6">
            {/* Portfolio summary strip */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard label="Current value" value={formatMoney(data.total_current_value)} accent />
              <MetricCard label="Total invested" value={formatMoney(data.total_invested)} />
              <MetricCard label="Realized P&L" value={formatMoney(data.total_realized_pnl)} />
              <MetricCard label="Unrealized P&L" value={formatMoney(data.total_unrealized_pnl)} />
            </div>
            {(data.largest_holding || data.best_performer || data.worst_performer) && (
              <div className="card flex flex-wrap gap-4">
                {data.largest_holding && (
                  <span className="text-sm text-text-secondary">
                    Largest: <strong className="text-text-primary">{data.largest_holding.ticker}</strong> {data.largest_holding.pct}% ({formatMoney(data.largest_holding.value)})
                  </span>
                )}
                {data.best_performer && (
                  <span className="text-sm text-green-400">
                    Best performer: {data.best_performer.ticker} ({formatMoney(data.best_performer.unrealized_pnl)})
                  </span>
                )}
                {data.worst_performer && data.worst_performer.ticker !== data.best_performer?.ticker && (
                  <span className="text-sm text-amber-400">
                    Worst performer: {data.worst_performer.ticker} ({formatMoney(data.worst_performer.unrealized_pnl)})
                  </span>
                )}
              </div>
            )}
            {/* Allocation by sector */}
            {data.allocation_by_sector && Object.keys(data.allocation_by_sector).length > 0 && (
              <div className="card">
                <h3 className="font-medium text-text-primary mb-2">Allocation by sector</h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(data.allocation_by_sector).map(([sector, pct]) => (
                    <span key={sector} className="px-2 py-1 rounded bg-surface-muted text-sm">
                      {sector}: {pct}%
                    </span>
                  ))}
                </div>
              </div>
            )}

            {(!data.holdings || data.holdings.length === 0) ? (
              <EmptyState message="No holdings. Add BUY transactions in Investments." />
            ) : (
              <>
                <div className="card overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-text-secondary border-b border-border">
                        <th className="pb-2 pr-4">Ticker</th>
                        <th className="pb-2 pr-4">Quantity</th>
                        <th className="pb-2 pr-4">Avg buy</th>
                        <th className="pb-2 pr-4">Invested</th>
                        <th className="pb-2 pr-4">Realized P&L</th>
                        <th className="pb-2 pr-4">Current price</th>
                        <th className="pb-2 pr-4">Current value</th>
                        <th className="pb-2 pr-4">Unrealized P&L</th>
                      </tr>
                    </thead>
                    <tbody className="text-text-primary">
                      {data.holdings.map((h) => (
                        <tr key={h.ticker} className="border-b border-border/50">
                          <td className="py-2 pr-4 font-medium">{h.ticker}</td>
                          <td className="py-2 pr-4">{h.quantity}</td>
                          <td className="py-2 pr-4">{formatMoney(h.avg_buy_price)}</td>
                          <td className="py-2 pr-4">{formatMoney(h.total_invested)}</td>
                          <td className="py-2 pr-4">{formatMoney(h.realized_pnl)}</td>
                          <td className="py-2 pr-4">{h.current_price != null ? formatMoney(h.current_price) : "—"}</td>
                          <td className="py-2 pr-4">{h.current_value != null ? formatMoney(h.current_value) : "—"}</td>
                          <td className="py-2 pr-4">{h.unrealized_pnl != null ? formatMoney(h.unrealized_pnl) : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {/* Latest transactions & dividend summary */}
            {((data.latest_transactions?.length ?? 0) > 0 || data.dividend_summary) && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.latest_transactions && (data.latest_transactions.length ?? 0) > 0 && (
                  <div className="card">
                    <h3 className="font-medium text-text-primary mb-2">Latest transactions</h3>
                    <ul className="text-sm space-y-1">
                      {data.latest_transactions.slice(0, 5).map((t, i) => (
                        <li key={t.id ?? i} className="text-text-secondary">
                          {t.date} {t.ticker} {t.transaction_type} {t.quantity} @ {t.price != null ? formatMoney(t.price) : "—"}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {data.dividend_summary && (
                  <div className="card">
                    <h3 className="font-medium text-text-primary mb-2">Dividends</h3>
                    <p className="text-sm text-text-secondary">
                      {data.dividend_summary.year} total: {formatMoney(data.dividend_summary.total_dividends)}
                    </p>
                  </div>
                )}
              </div>
            )}
            {portfolioSuggestions.length > 0 && (
              <div className="card">
                <h3 className="font-medium text-text-primary mb-2">Portfolio suggestions</h3>
                <ul className="space-y-1 text-sm">
                  {portfolioSuggestions.map((s) => (
                    <li key={s.id} className="text-text-secondary">{s.message}</li>
                  ))}
                </ul>
                <Link to={WEALTH_ROUTES.suggestions} className="text-accent hover:underline text-sm mt-2 inline-block">View all suggestions</Link>
              </div>
            )}
                {data.holdings.some((h) => h.total_invested > 0) && (
                  <div className="card" style={{ height: 320 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={data.holdings.map((h) => ({ name: h.ticker, value: h.total_invested }))}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={100}
                          paddingAngle={2}
                          dataKey="value"
                          nameKey="name"
                          label={({ name, value }) => `${name} ${formatMoney(value)}`}
                        >
                          {data.holdings.map((h, i) => (
                            <Cell key={h.ticker} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(v: unknown) => formatMoney(Number(v))} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </>
            )}

            {/* Advanced: Discover stocks & affordability */}
            <details className="card">
              <summary className="cursor-pointer font-medium text-text-primary list-none flex items-center justify-between gap-2">
                <span>Discover stocks & check affordability</span>
                <span className="text-text-muted text-sm font-normal">Search, get picks for you, and see if you can buy</span>
              </summary>
              <div className="pt-4 mt-4 border-t border-border space-y-6">
                {diversification && diversification.suggestions.length > 0 && (
                  <div>
                    <h4 className="font-medium text-text-primary mb-2">Stocks that work for you</h4>
                    <p className="text-sm text-text-secondary mb-3">
                      You hold {diversification.your_holdings.join(", ") || "nothing"}
                      {diversification.your_sectors.length > 0 && ` in sectors: ${diversification.your_sectors.join(", ")}. `}
                      Consider adding these to diversify.
                    </p>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-text-secondary border-b border-border">
                            <th className="pb-2 pr-4">Ticker</th>
                            <th className="pb-2 pr-4">Name</th>
                            <th className="pb-2 pr-4">Sector</th>
                            <th className="pb-2 pr-4">Price</th>
                            <th className="pb-2 pr-4">Div</th>
                            <th className="pb-2 pr-4">Why</th>
                            <th className="pb-2"></th>
                          </tr>
                        </thead>
                        <tbody className="text-text-primary">
                          {diversification.suggestions.slice(0, 8).map((s: DiversificationSuggestion) => (
                            <tr key={s.ticker} className="border-b border-border/50">
                              <td className="py-2 pr-4 font-medium">{s.ticker}</td>
                              <td className="py-2 pr-4">{s.stock_name ?? "—"}</td>
                              <td className="py-2 pr-4">{s.sector ?? "—"}</td>
                              <td className="py-2 pr-4">{s.current_price != null ? formatMoney(s.current_price) : "—"}</td>
                              <td className="py-2 pr-4">{s.dividend_yield != null ? `${s.dividend_yield}%` : "—"}</td>
                              <td className="py-2 pr-4 text-text-secondary">{s.reason ?? "—"}</td>
                              <td className="py-2 flex gap-2 flex-wrap">
                                <button type="button" className="text-sm text-accent hover:underline" onClick={() => useTickerForLookup(s.ticker, s.current_price ?? undefined)}>Use</button>
                                {watchlistAdded.has(s.ticker.toUpperCase()) ? (
                                  <span className="text-sm text-text-muted">Added</span>
                                ) : (
                                  <button type="button" className="text-sm text-accent hover:underline" onClick={() => handleAddToWatchlist(s.ticker, s.stock_name, s.sector, s.current_price)}>Add to Watchlist</button>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                <div>
                  <h4 className="font-medium text-text-primary mb-2">Search stocks</h4>
                  <div className="flex flex-wrap gap-4 items-end">
                    <label className="block">
                      <span className="text-sm text-text-secondary">Ticker or name</span>
                      <input className="input-field mt-1 w-56" placeholder="e.g. AAPL or Apple" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSearchStocks()} />
                    </label>
                    <button type="button" className="btn-primary" onClick={handleSearchStocks} disabled={searchLoading}>{searchLoading ? "Searching…" : "Search"}</button>
                  </div>
                  {searchResults.length > 0 && (
                    <div className="mt-3 overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-text-secondary border-b border-border">
                            <th className="pb-2 pr-4">Ticker</th>
                            <th className="pb-2 pr-4">Name</th>
                            <th className="pb-2 pr-4">Sector</th>
                            <th className="pb-2 pr-4">Price</th>
                            <th className="pb-2"></th>
                          </tr>
                        </thead>
                        <tbody className="text-text-primary">
                          {searchResults.map((s) => (
                            <tr key={s.ticker} className="border-b border-border/50">
                              <td className="py-2 pr-4 font-medium">{s.ticker}</td>
                              <td className="py-2 pr-4">{s.stock_name ?? "—"}</td>
                              <td className="py-2 pr-4">{s.sector ?? "—"}</td>
                              <td className="py-2 pr-4">{s.current_price != null ? formatMoney(s.current_price) : "—"}</td>
                              <td className="py-2 flex gap-2 flex-wrap">
                                <button type="button" className="text-sm text-accent hover:underline" onClick={() => useTickerForLookup(s.ticker, s.current_price ?? undefined)}>Use for affordability</button>
                                {watchlistAdded.has(s.ticker.toUpperCase()) ? (
                                  <span className="text-sm text-text-muted">Added</span>
                                ) : (
                                  <button type="button" className="text-sm text-accent hover:underline" onClick={() => handleAddToWatchlist(s.ticker, s.stock_name, s.sector, s.current_price)}>Add to Watchlist</button>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
                <div>
                  <h4 className="font-medium text-text-primary mb-2">Can I buy this?</h4>
                  <div className="flex flex-wrap gap-4 items-end">
                    <label className="block">
                      <span className="text-sm text-text-secondary">Ticker</span>
                      <input className="input-field mt-1 w-28" value={tickerLookup} onChange={(e) => setTickerLookup(e.target.value)} placeholder="AAPL" />
                    </label>
                    <button type="button" className="btn-secondary" onClick={handleStockLookup}>Details</button>
                    <label className="block">
                      <span className="text-sm text-text-secondary">Qty</span>
                      <input type="number" className="input-field mt-1 w-20" min={0} step={1} value={affQty} onChange={(e) => setAffQty(Number(e.target.value))} />
                    </label>
                    <label className="block">
                      <span className="text-sm text-text-secondary">Price</span>
                      <input type="number" className="input-field mt-1 w-24" min={0} step={0.01} value={affPrice} onChange={(e) => setAffPrice(Number(e.target.value))} />
                    </label>
                    <button type="button" className="btn-primary" onClick={handleAffordability}>Check</button>
                  </div>
                  {stockDetails && (
                    <div className="mt-3 p-3 rounded-lg bg-surface-muted text-sm flex flex-wrap items-center justify-between gap-2">
                      <p><strong>{stockDetails.ticker}</strong> {stockDetails.stock_name ?? ""} · {stockDetails.current_price != null ? formatMoney(stockDetails.current_price) : ""} {stockDetails.sector ? `· ${stockDetails.sector}` : ""}</p>
                      {watchlistAdded.has(stockDetails.ticker.toUpperCase()) ? (
                        <span className="text-text-muted">In watchlist</span>
                      ) : (
                        <button type="button" className="text-sm text-accent hover:underline" onClick={() => handleAddToWatchlist(stockDetails.ticker, stockDetails.stock_name, stockDetails.sector, stockDetails.current_price)}>Add to Watchlist</button>
                      )}
                    </div>
                  )}
                  {affResult && (
                    <div className={`mt-3 p-3 rounded-lg text-sm ${affResult.affordable ? "bg-green-500/10 text-green-200" : "bg-amber-500/10 text-amber-200"}`}>
                      <p className="font-medium">{affResult.message}</p>
                      <p className="text-text-muted">Free cash: {formatMoney(affResult.free_cash)} · Cost: {formatMoney(affResult.cost)}</p>
                      {affResult.reasons.length > 0 && <ul className="list-disc list-inside mt-2">{affResult.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>}
                    </div>
                  )}
                </div>
              </div>
            </details>
          </div>
        )}
      </PageContent>
    </>
  );
}
