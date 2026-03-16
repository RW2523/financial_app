const getBaseUrl = () => {
  const url = (typeof window !== "undefined" && (window as unknown as { __API_URL?: string }).__API_URL) ||
    import.meta.env.VITE_EXPENSE_API_URL ||
    "http://127.0.0.1:8000";
  return String(url).replace(/\/$/, "");
};

let _apiUserId: string | null = null;

export function setApiUserId(userId: string | null) {
  _apiUserId = userId;
}

/** Headers to add to API requests (e.g. X-User-Id). Use for fetch() calls that don't go through apiFetch. */
export function getApiHeaders(): Record<string, string> {
  const h: Record<string, string> = {};
  if (_apiUserId) h["X-User-Id"] = _apiUserId;
  return h;
}

export function apiUrl(): string {
  return getBaseUrl();
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { params?: Record<string, string | number> } = {}
): Promise<T> {
  const { params, ...init } = options;
  let url = `${getBaseUrl()}${path}`;
  if (params && Object.keys(params).length > 0) {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => search.set(k, String(v)));
    url += `?${search.toString()}`;
  }
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(init.headers as Record<string, string>) };
  if (_apiUserId) headers["X-User-Id"] = _apiUserId;
  const res = await fetch(url, {
    ...init,
    headers,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  if (res.headers.get("content-type")?.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  return undefined as T;
}

// Expenses
export interface Expense {
  id?: number;
  date: string;
  category: string;
  amount: number;
  currency: string;
  raw_text?: string;
  is_verified?: number;
  confidence_score?: number;
}

export async function getExpenses(): Promise<Expense[]> {
  return apiFetch<Expense[]>("/expenses");
}

export async function addTextExpense(text: string): Promise<Expense> {
  return apiFetch<Expense>("/add-text-expense", { method: "POST", body: JSON.stringify({ text }) });
}

export async function addAudioExpense(file: Blob): Promise<Expense> {
  const base = getBaseUrl();
  const form = new FormData();
  form.append("file", file, "audio.wav");
  const res = await fetch(`${base}/add-audio-expense`, { method: "POST", body: form, headers: getApiHeaders() });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getReviewQueue(): Promise<Expense[]> {
  return apiFetch<Expense[]>("/expenses/review");
}

export async function verifyExpense(id: number, payload: { date?: string; category?: string; amount?: number; currency?: string }): Promise<Expense> {
  return apiFetch<Expense>(`/expenses/${id}/verify`, { method: "POST", body: JSON.stringify(payload) });
}

export async function deleteExpense(id: number): Promise<void> {
  await apiFetch(`/expenses/${id}`, { method: "DELETE" });
}

// Monthly summary
export async function getMonthlySummary(year: number, month: number): Promise<{ total_expenses: number; summary: string; expenses?: Expense[] }> {
  return apiFetch("/monthly-summary", { method: "POST", body: JSON.stringify({ year, month }) });
}

// Limits
export interface LimitStatus {
  year: number;
  month: number;
  limits: { category: string; amount: number; currency?: string }[];
  spending: Record<string, number>;
  alerts: { category: string; limit: number; spent: number; percent: number; alert_type: string }[];
}

export async function getLimitsStatus(year?: number, month?: number): Promise<LimitStatus> {
  const params: Record<string, number> = {};
  if (year != null) params.year = year;
  if (month != null) params.month = month;
  return apiFetch<LimitStatus>("/limits/status", { params });
}

export async function getLimits(): Promise<{ category: string; amount: number; currency?: string }[]> {
  return apiFetch("/limits");
}

export async function setLimit(category: string, amount: number, currency = "USD"): Promise<void> {
  await apiFetch("/limits", { method: "POST", body: JSON.stringify({ category, amount, currency }) });
}

export async function deleteLimit(category: string): Promise<void> {
  await apiFetch(`/limits/${category}`, { method: "DELETE" });
}

// Forecast & alerts
export async function getForecastMonth(year?: number, month?: number): Promise<{ projected_total: number; by_category?: Record<string, number>; days_elapsed?: number; days_in_month?: number }> {
  return apiFetch("/forecast/month", { params: year != null && month != null ? { year, month } : {} });
}

export async function getForecastCategories(year?: number, month?: number): Promise<Record<string, number> | unknown[]> {
  return apiFetch("/forecast/categories", { params: year != null && month != null ? { year, month } : {} });
}

export async function getPredictiveAlerts(year?: number, month?: number): Promise<{ alerts: { message: string }[] }> {
  return apiFetch("/alerts/predictive", { params: year != null && month != null ? { year, month } : {} });
}

// Insights
export async function getInsightsOverview(params: { start_date?: string; end_date?: string }): Promise<Record<string, unknown>> {
  return apiFetch("/insights/overview", { params: params as Record<string, string> });
}

export async function getInsightsCategories(params: { start_date?: string; end_date?: string }): Promise<unknown> {
  return apiFetch("/insights/categories", { params: params as Record<string, string> });
}

export async function getInsightsHealthScore(): Promise<{ score: number; metrics?: Record<string, unknown> }> {
  return apiFetch("/insights/health-score");
}

export async function getInsightsTrends(months?: number): Promise<{ trends?: { label: string; total_spend: number; transaction_count: number }[] }> {
  return apiFetch("/insights/trends", { params: months != null ? { months } : {} });
}

export async function getInsightsRecommendations(): Promise<{ recommendations?: { title: string; suggestion: string; metric_cited?: string; value?: unknown }[] }> {
  return apiFetch("/insights/recommendations");
}

export async function getInsightsAnomalies(params: { start_date?: string; end_date?: string }): Promise<{ anomalies?: unknown[] }> {
  return apiFetch("/insights/anomalies", { params: params as Record<string, string> });
}

export async function getInsightsNarrative(params: { start_date?: string; end_date?: string }): Promise<{ narrative?: string }> {
  return apiFetch("/insights/narrative", { params: params as Record<string, string> });
}

export async function getRecurring(): Promise<{ items?: unknown[] }> {
  return apiFetch("/insights/recurring");
}

export async function recomputeRecurring(): Promise<unknown> {
  return apiFetch("/insights/recurring/recompute", { method: "POST" });
}

// Ask
export async function ask(question: string): Promise<{ answer: string; filters_used?: unknown; supporting_data?: unknown }> {
  return apiFetch("/ask", { method: "POST", body: JSON.stringify({ question }) });
}

// Chat (unified add + ask)
export type ChatResponse =
  | { type: "expense_added"; expense: { id?: number; date: string; category: string; amount: number; currency: string; raw_text?: string }; message: string }
  | { type: "answer"; answer_text: string; question: string; refused?: boolean; rows?: unknown[]; aggregates?: unknown };

export async function chat(
  message: string,
  history?: { role: string; content: string }[]
): Promise<ChatResponse> {
  return apiFetch("/chat", {
    method: "POST",
    body: JSON.stringify({ message, history: history ?? [] }),
  });
}

export async function chatVoice(file: Blob): Promise<ChatResponse & { transcript?: string }> {
  const base = getBaseUrl();
  const form = new FormData();
  form.append("file", file, "audio.wav");
  const res = await fetch(`${base}/chat-voice`, { method: "POST", body: form, headers: getApiHeaders() });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export interface DocumentExpensesResponse {
  added: number;
  expenses: Expense[];
  message: string;
  ocr_available?: boolean;
  pdf_available?: boolean;
}

export async function addDocumentExpenses(
  files: File[],
  message?: string
): Promise<DocumentExpensesResponse> {
  const base = getBaseUrl();
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  if (message != null && message.trim()) form.append("message", message.trim());
  const res = await fetch(`${base}/add-document-expenses`, {
    method: "POST",
    body: form,
    headers: getApiHeaders(),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Goals
export interface Goal {
  id: number;
  goal_type: string;
  target_amount: number;
  current_amount: number;
  target_date?: string;
  category?: string;
  description?: string;
  status?: string;
  distance?: Record<string, unknown>;
  suggested_reduction_per_month?: number;
  suggested_reduction_per_week?: number;
}

export async function getGoals(status = "active"): Promise<Goal[]> {
  return apiFetch<Goal[]>("/goals", { params: { status } });
}

export async function createGoal(payload: {
  goal_type: string;
  target_amount: number;
  current_amount: number;
  target_date?: string | null;
  category?: string | null;
  description?: string | null;
}): Promise<Goal> {
  return apiFetch<Goal>("/goals", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateGoal(id: number, payload: Partial<Goal>): Promise<Goal> {
  return apiFetch<Goal>(`/goals/${id}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteGoal(id: number): Promise<void> {
  await apiFetch(`/goals/${id}`, { method: "DELETE" });
}

// Affordability
export async function checkAffordability(payload: { amount: number; category?: string | null; merchant?: string | null }): Promise<{
  can_afford: boolean;
  recommendation_text: string;
  reasons: string[];
  projected_impact?: unknown;
  budget_impact?: unknown;
  goal_impact?: unknown;
}> {
  return apiFetch("/affordability/check", { method: "POST", body: JSON.stringify(payload) });
}

// Simulate
export interface SimulateAdjustment {
  type: string;
  category?: string;
  value?: number;
  amount?: number;
  merchant?: string;
}

export async function simulate(adjustments: SimulateAdjustment[]): Promise<{
  baseline_summary?: { projected_total?: number; by_category?: Record<string, number> };
  simulated_summary?: { projected_total?: number; by_category?: Record<string, number> };
  delta_summary?: { total_change?: number };
  projected_limit_changes?: unknown[];
  goal_impact?: unknown[];
}> {
  return apiFetch("/simulate", { method: "POST", body: JSON.stringify({ adjustments }) });
}

// Gmail
export async function getGmailStatus(): Promise<{
  connected?: boolean;
  configured?: boolean;
  message?: string;
  credentials_path?: string;
  token_path?: string;
  error?: string;
}> {
  return apiFetch("/gmail/status");
}

export async function syncGmail(body?: { query?: string; max_results?: number }): Promise<{ added?: number; errors?: string[] }> {
  return apiFetch("/gmail/sync", { method: "POST", body: JSON.stringify(body ?? {}) });
}

// Clear all data (Settings). Backend also returns wealth table counts when present.
export async function clearAllData(): Promise<{
  ok: boolean;
  deleted: {
    expenses: number;
    limits: number;
    goals: number;
    recurring: number;
    gmail_processed: number;
    salary_income?: number;
    investment_transactions?: number;
    portfolio_snapshots?: number;
    stock_watchlist?: number;
    wealth_liabilities?: number;
  };
}> {
  return apiFetch("/admin/clear-data", { method: "POST", body: JSON.stringify({ confirm: true }) });
}

// Add sample data (expenses, limits, goals, and Wealth Hub: salary, investments, watchlist, liabilities).
export async function addSampleData(): Promise<{
  ok: boolean;
  expenses: number;
  limits: number;
  goals: number;
  salary_records?: number;
  investments?: number;
  watchlist?: number;
  liabilities?: number;
}> {
  return apiFetch("/admin/seed-sample-data", { method: "POST" });
}

// Finance news (Tavily)
export interface FinanceNewsItem {
  title: string;
  url: string;
  content: string;
  score?: number;
}

export async function getFinanceNews(params?: { query?: string; max_results?: number; time_range?: string }): Promise<{
  results: FinanceNewsItem[];
  query?: string;
  response_time?: number;
  error?: string;
}> {
  const search = new URLSearchParams();
  if (params?.query) search.set("query", params.query);
  if (params?.max_results != null) search.set("max_results", String(params.max_results));
  if (params?.time_range) search.set("time_range", params.time_range);
  const qs = search.toString();
  return apiFetch(`/news/finance${qs ? `?${qs}` : ""}`);
}

// Auth
export interface AuthUser {
  user_id: string;
  username: string;
  salary: number;
  monthly_budget: number;
  currency: string;
  display_name?: string;
}

export async function authLogin(username: string, password: string): Promise<AuthUser> {
  return apiFetch("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
}

export async function authRegister(params: {
  username: string;
  password: string;
  salary?: number;
  monthly_budget?: number;
  currency?: string;
}): Promise<AuthUser> {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      username: params.username,
      password: params.password,
      salary: params.salary ?? 0,
      monthly_budget: params.monthly_budget ?? 0,
      currency: params.currency ?? "USD",
    }),
  });
}

// Health
export async function apiHealth(): Promise<{ status?: string }> {
  return apiFetch("/");
}

// ---------- Wealth Hub ----------

export interface SalaryRecord {
  id: number;
  date: string;
  source: string;
  gross_amount: number;
  deductions: number;
  net_amount: number;
  bonus_amount: number;
  notes?: string | null;
  created_at?: string;
}

export interface SalarySummary {
  year: number;
  month: number;
  net_income: number;
  bonus_total: number;
  gross_total?: number;
  deductions_total?: number;
  record_count?: number;
}

export async function getSalaryRecords(params?: { year?: number; month?: number }): Promise<SalaryRecord[]> {
  const search = new URLSearchParams();
  if (params?.year != null) search.set("year", String(params.year));
  if (params?.month != null) search.set("month", String(params.month));
  const qs = search.toString();
  return apiFetch<SalaryRecord[]>(`/wealth/salary${qs ? `?${qs}` : ""}`);
}

export async function createSalaryRecord(payload: {
  date: string;
  source: string;
  gross_amount: number;
  deductions?: number;
  net_amount?: number;
  bonus_amount?: number;
  notes?: string | null;
}): Promise<SalaryRecord> {
  return apiFetch<SalaryRecord>("/wealth/salary", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateSalaryRecord(id: number, payload: Partial<SalaryRecord>): Promise<SalaryRecord> {
  return apiFetch<SalaryRecord>(`/wealth/salary/${id}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteSalaryRecord(id: number): Promise<void> {
  await apiFetch(`/wealth/salary/${id}`, { method: "DELETE" });
}

export async function getSalarySummary(year?: number, month?: number): Promise<SalarySummary> {
  const params: Record<string, number> = {};
  if (year != null) params.year = year;
  if (month != null) params.month = month;
  return apiFetch<SalarySummary>("/wealth/salary/summary", { params });
}

export interface InvestmentTransaction {
  id: number;
  ticker: string;
  stock_name?: string | null;
  transaction_type: string;
  quantity: number;
  price: number;
  fees: number;
  date: string;
  broker?: string | null;
  notes?: string | null;
  created_at?: string;
}

export async function getInvestmentTransactions(): Promise<InvestmentTransaction[]> {
  return apiFetch<InvestmentTransaction[]>("/wealth/investments");
}

export async function createInvestmentTransaction(payload: {
  ticker: string;
  stock_name?: string | null;
  transaction_type: string;
  quantity: number;
  price: number;
  fees?: number;
  date: string;
  broker?: string | null;
  notes?: string | null;
}): Promise<InvestmentTransaction> {
  return apiFetch<InvestmentTransaction>("/wealth/investments", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateInvestmentTransaction(id: number, payload: Partial<InvestmentTransaction>): Promise<InvestmentTransaction> {
  return apiFetch<InvestmentTransaction>(`/wealth/investments/${id}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteInvestmentTransaction(id: number): Promise<void> {
  await apiFetch(`/wealth/investments/${id}`, { method: "DELETE" });
}

export interface PortfolioHolding {
  ticker: string;
  stock_name: string;
  quantity: number;
  avg_buy_price: number;
  total_invested: number;
  realized_pnl: number;
  current_price?: number | null;
  current_value?: number | null;
  unrealized_pnl?: number | null;
}

export interface PortfolioSummary {
  holdings: PortfolioHolding[];
  total_invested: number;
  total_realized_pnl: number;
  total_current_value: number;
  total_unrealized_pnl: number;
  largest_holding?: { ticker: string; value: number; pct: number } | null;
  best_performer?: { ticker: string; unrealized_pnl: number } | null;
  worst_performer?: { ticker: string; unrealized_pnl: number } | null;
  allocation_by_sector?: Record<string, number>;
  latest_transactions?: { id?: number; date?: string; ticker?: string; transaction_type?: string; quantity?: number; price?: number }[];
  dividend_summary?: { year: number; total_dividends: number };
}

export async function getPortfolioSummary(): Promise<PortfolioSummary> {
  return apiFetch<PortfolioSummary>("/wealth/portfolio");
}

export interface CashflowSummary {
  year: number;
  month: number;
  total_income: number;
  total_expenses: number;
  total_invested: number;
  net_savings: number;
  free_cash: number;
  savings_ratio: number;
  investment_ratio: number;
  expense_ratio: number;
  safe_investable_surplus?: number;
  aggressive_investable_surplus?: number;
  remaining_buffer?: number;
  fixed_expenses?: number;
  variable_expenses?: number;
  mom_previous_income?: number;
  mom_previous_expenses?: number;
  mom_previous_invested?: number;
  mom_previous_savings?: number;
  mom_delta_income?: number;
  mom_delta_expenses?: number;
  mom_delta_invested?: number;
  mom_delta_savings?: number;
}

export async function getCashflowSummary(year?: number, month?: number): Promise<CashflowSummary> {
  const params: Record<string, number> = {};
  if (year != null) params.year = year;
  if (month != null) params.month = month;
  return apiFetch<CashflowSummary>("/wealth/cashflow", { params });
}

export interface ProjectionScenario {
  id: string;
  label: string;
  description: string;
  projected_monthly_surplus: number;
  projected_yearly_invested: number;
  portfolio_1y: number;
}

export interface ProjectionsSummary {
  year: number;
  month: number;
  projected_end_of_month_expenses: number;
  projected_monthly_surplus: number;
  projected_yearly_invested: number;
  portfolio_projection: { "6m": number; "1y": number; "3y": number };
  portfolio_growth_mode: string;
  annual_return_assumption?: number;
  current_portfolio_value?: number;
  scenarios?: ProjectionScenario[];
}

export async function getProjections(year?: number, month?: number, portfolio_growth_mode?: string): Promise<ProjectionsSummary> {
  const params: Record<string, string | number> = {};
  if (year != null) params.year = year;
  if (month != null) params.month = month;
  if (portfolio_growth_mode) params.portfolio_growth_mode = portfolio_growth_mode;
  return apiFetch<ProjectionsSummary>("/wealth/projections", { params });
}

export interface Suggestion {
  id: string;
  title: string;
  message: string;
  why_this_matters?: string;
  destination?: string;
  metric: string;
  value: number;
  severity: string;
}

export async function getSuggestions(year?: number, month?: number): Promise<{ year: number; month: number; suggestions: Suggestion[] }> {
  const params: Record<string, number> = {};
  if (year != null) params.year = year;
  if (month != null) params.month = month;
  return apiFetch("/wealth/suggestions", { params });
}

export interface StockDetails {
  ticker: string;
  stock_name?: string | null;
  sector?: string | null;
  current_price?: number | null;
  change?: number | null;
  market_cap?: string | null;
  pe_ratio?: number | null;
  dividend_yield?: number | null;
  range_52w?: string | null;
  source: string;
}

export async function getStockDetails(ticker: string): Promise<StockDetails> {
  return apiFetch<StockDetails>("/wealth/stock/details", { params: { ticker: ticker.trim() } });
}

/** Search/list stocks by ticker or name. Empty q returns all. */
export async function searchStocks(q: string = ""): Promise<StockDetails[]> {
  return apiFetch<StockDetails[]>("/wealth/stock/search", { params: q ? { q } : {} });
}

export interface DiversificationSuggestion extends StockDetails {
  reason?: string;
}

export interface DiversificationResult {
  your_holdings: string[];
  your_sectors: string[];
  suggestions: DiversificationSuggestion[];
}

export async function getDiversificationSuggestions(): Promise<DiversificationResult> {
  return apiFetch<DiversificationResult>("/wealth/stock/diversification");
}

/** Portfolio Manager / Portfolio Intelligence */
export interface PortfolioManagerView {
  total_portfolio_value: number;
  allocation_by_sector: Record<string, number>;
  diversification_score: number;
  diversification_explanation?: string;
  sector_gaps?: string[];
  rebalancing_impact_preview?: { current_score: number; potential_score: number; message: string };
  stocks_that_work_for_you: {
    ticker: string;
    stock_name?: string | null;
    sector?: string | null;
    current_price?: number | null;
    dividend_yield?: number | null;
    why_for_you: string;
  }[];
  rebalancing_suggestions: {
    sector: string;
    suggestion: string;
    top_pick: string;
    top_pick_name?: string;
    price?: number;
  }[];
  your_holdings_count: number;
  sectors_held: string[];
}

export async function getPortfolioManagerView(): Promise<PortfolioManagerView> {
  return apiFetch<PortfolioManagerView>("/wealth/manager");
}

export interface StockAffordabilityResult {
  affordable: boolean;
  message: string;
  free_cash: number;
  cost: number;
  concentration_risk?: boolean;
  reasons: string[];
}

export async function checkStockAffordability(payload: {
  ticker: string;
  quantity: number;
  price_per_share: number;
}): Promise<StockAffordabilityResult> {
  return apiFetch<StockAffordabilityResult>("/wealth/stock/affordability", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ---------- Wealth Overview, Score, Net Worth ----------

export interface WealthOverviewResponse {
  year: number;
  month: number;
  summary_strip: {
    net_income_this_month: number;
    total_expenses_this_month: number;
    free_cash_this_month: number;
    invested_this_month: number;
    portfolio_value: number;
    net_worth?: number | null;
    wealth_score?: number | null;
  };
  priority_alerts: { id: string; title: string; message: string; severity: string; destination?: string }[];
  next_actions: { action: string; destination: string; reason: string }[];
  wealth_score: number | null;
  wealth_score_factors: Record<string, number>;
  net_worth_preview: { net_worth: number; total_assets: number; total_liabilities: number; delta_vs_previous_month?: number | null } | null;
  goals_preview: { id: number; description: string; current: number; target: number; progress_pct: number }[];
  has_goals: boolean;
}

export async function getWealthOverview(year?: number, month?: number): Promise<WealthOverviewResponse> {
  const params: Record<string, number> = {};
  if (year != null) params.year = year;
  if (month != null) params.month = month;
  return apiFetch<WealthOverviewResponse>("/wealth/overview", { params });
}

export async function getWealthScore(): Promise<{ score: number; factors: Record<string, number>; weights: Record<string, number> }> {
  return apiFetch("/wealth/score");
}

export interface NetWorthResponse {
  year: number;
  month: number;
  total_assets: number;
  total_liabilities: number;
  net_worth: number;
  assets_breakdown: { free_cash: number; portfolio_value: number };
  liabilities_count: number;
  delta_vs_previous_month?: number | null;
}

export async function getNetWorth(year?: number, month?: number): Promise<NetWorthResponse> {
  const params: Record<string, number> = {};
  if (year != null) params.year = year;
  if (month != null) params.month = month;
  return apiFetch<NetWorthResponse>("/wealth/net-worth", { params });
}

// ---------- Watchlist ----------

export interface WatchlistItem {
  id: number;
  ticker: string;
  stock_name?: string | null;
  target_buy_price?: number | null;
  current_price?: number | null;
  sector?: string | null;
  notes?: string | null;
  added_at?: string;
}

export async function getWatchlist(): Promise<WatchlistItem[]> {
  return apiFetch<WatchlistItem[]>("/wealth/watchlist");
}

export async function addWatchlistItem(payload: {
  ticker: string;
  stock_name?: string | null;
  target_buy_price?: number | null;
  current_price?: number | null;
  sector?: string | null;
  notes?: string | null;
}): Promise<WatchlistItem> {
  return apiFetch<WatchlistItem>("/wealth/watchlist", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateWatchlistItem(id: number, payload: { target_buy_price?: number; current_price?: number; notes?: string }): Promise<WatchlistItem> {
  return apiFetch<WatchlistItem>(`/wealth/watchlist/${id}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteWatchlistItem(id: number): Promise<void> {
  await apiFetch(`/wealth/watchlist/${id}`, { method: "DELETE" });
}

// ---------- Liabilities ----------

export interface Liability {
  id: number;
  name: string;
  balance: number;
  liability_type?: string | null;
  notes?: string | null;
  updated_at?: string;
}

export async function getLiabilities(): Promise<Liability[]> {
  return apiFetch<Liability[]>("/wealth/liabilities");
}

export async function createLiability(payload: { name: string; balance: number; liability_type?: string | null; notes?: string | null }): Promise<Liability> {
  return apiFetch<Liability>("/wealth/liabilities", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateLiability(id: number, payload: Partial<Liability>): Promise<Liability> {
  return apiFetch<Liability>(`/wealth/liabilities/${id}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteLiability(id: number): Promise<void> {
  await apiFetch(`/wealth/liabilities/${id}`, { method: "DELETE" });
}
