import { useState, useEffect } from "react";
import { ExternalLink, RefreshCw, Newspaper } from "lucide-react";
import PageHeader from "../components/PageHeader";
import { PageContent } from "../components/ui";
import { getFinanceNews, type FinanceNewsItem } from "../api/client";

const TIME_RANGES = [
  { value: "day", label: "Last 24 hours" },
  { value: "week", label: "Last week" },
  { value: "month", label: "Last month" },
  { value: "year", label: "Last year" },
] as const;

export default function FinanceNews() {
  const [results, setResults] = useState<FinanceNewsItem[]>([]);
  const [query, setQuery] = useState<string>("");
  const [apiQuery, setApiQuery] = useState<string>("");
  const [timeRange, setTimeRange] = useState<string>("week");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [responseTime, setResponseTime] = useState<number | null>(null);

  const fetchNews = async (customQuery?: string, customTimeRange?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getFinanceNews({
        query: customQuery || undefined,
        max_results: 18,
        time_range: customTimeRange || timeRange,
      });
      setResults(res.results ?? []);
      setApiQuery(res.query ?? "");
      setResponseTime(res.response_time ?? null);
      if (res.error) setError(res.error);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load finance news.");
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNews();
  }, []);

  const handleSearch = () => {
    fetchNews(query || undefined, timeRange);
  };

  const handleTimeRangeChange = (range: string) => {
    setTimeRange(range);
    fetchNews(query || undefined, range);
  };

  return (
    <>
      <PageHeader
        title="Finance News"
        subtitle="Money, exchange rates, stocks, economy — powered by Tavily. Set TAVILY_API_KEY to enable."
      />
      <PageContent loading={loading} loadingMessage="Fetching finance news…">
        <div className="p-6 max-w-4xl space-y-6">
          <div className="card flex flex-col sm:flex-row gap-3 flex-wrap">
            <input
              type="text"
              className="input-field flex-1 min-w-[200px]"
              placeholder="Search (e.g. Fed rates, Bitcoin, EUR/USD)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              aria-label="Search finance news"
            />
            <select
              className="input-field w-auto"
              value={timeRange}
              onChange={(e) => handleTimeRangeChange(e.target.value)}
              aria-label="Time range"
            >
              {TIME_RANGES.map(({ value, label }) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn-primary flex items-center gap-2"
              onClick={handleSearch}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              {loading ? "Loading…" : "Search"}
            </button>
          </div>

          {error && (
            <div className="card border-amber-500/40 bg-amber-500/5 text-amber-200">
              <p className="text-sm">{error}</p>
              <p className="text-xs text-text-muted mt-2">
                Add TAVILY_API_KEY to your .env (get a key at tavily.com) and restart the backend.
              </p>
            </div>
          )}

          {!error && (apiQuery || results.length > 0) && (
            <div className="text-sm text-text-muted">
              {apiQuery && <span>Query: “{apiQuery}”</span>}
              {responseTime != null && <span className="ml-3">Fetched in {responseTime.toFixed(1)}s</span>}
            </div>
          )}

          {!error && results.length === 0 && !loading && (
            <div className="card flex flex-col items-center justify-center py-12 text-text-secondary">
              <Newspaper className="h-12 w-12 mb-3 opacity-50" />
              <p>No finance news results. Try a different search or time range.</p>
            </div>
          )}

          {results.length > 0 && (
            <ul className="space-y-4">
              {results.map((item, i) => (
                <li key={i} className="card hover:border-accent/40 transition-colors">
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block group"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-medium text-text-primary group-hover:text-accent">
                        {item.title || "No title"}
                      </h3>
                      <ExternalLink className="h-4 w-4 shrink-0 text-text-muted group-hover:text-accent" />
                    </div>
                    {item.content && (
                      <p className="mt-2 text-sm text-text-secondary line-clamp-2">
                        {item.content}
                      </p>
                    )}
                    <p className="mt-2 text-xs text-text-muted truncate" title={item.url}>
                      {item.url}
                    </p>
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      </PageContent>
    </>
  );
}
