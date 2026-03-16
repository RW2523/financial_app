# Wealth Hub Upgrade — Delivery Summary

## What was changed

The Wealth Hub was upgraded from isolated tabs into a guided, insight-driven financial workspace with:

- **Navigation**: Grouped tabs (Money In, Wealth Build, Guidance, Planning); Manager renamed to **Portfolio Intelligence** (route `/wealth/manager` unchanged).
- **Overview**: Command-center dashboard with summary strip, priority alerts, “What should I do next?”, wealth flow, goal preview, net worth preview.
- **Persistent summary bar**: Income, expenses, free cash, invested, portfolio, Wealth Score across all Wealth Hub tabs.
- **Portfolio**: Summary strip (largest holding, best/worst performer), allocation by sector, latest transactions, dividend summary, contextual suggestions, “Add to Watchlist” in discovery.
- **Cashflow**: Monthly flow view, flow breakdown (Income → Expenses → Investments → Remaining), ratios, fixed vs variable, investable surplus (safe/aggressive/buffer), month-over-month comparison, mini-suggestions.
- **Projections**: Scenario comparison (current pace, disciplined spending, increased investing, reduced expenses), projected guidance.
- **Portfolio Intelligence**: Diversification explanation, sector gap analysis, rebalancing impact preview; same rebalancing and “stocks that work for you” as before.
- **Suggestions**: Sorted by severity; each has “why this matters” and destination link.
- **Goals**: New tab at `/wealth/goals` (uses existing goals API; wealth-oriented goal types).
- **Watchlist**: New tab at `/wealth/watchlist`; add from Portfolio discovery.
- **Net Worth**: New tab at `/wealth/net-worth` (assets, liabilities, delta vs previous month).
- **Wealth Score**: Deterministic 0–100 score used in Overview and summary bar.

---

## Modified files

### Backend
- `backend/wealth_portfolio_service.py` — `get_portfolio_summary(include_enrichment=True)` adds largest_holding, best_performer, worst_performer, allocation_by_sector, latest_transactions, dividend_summary.
- `backend/wealth_cashflow_service.py` — safe/aggressive investable surplus, remaining_buffer, fixed_expenses, variable_expenses, mom_* fields.
- `backend/wealth_projections_service.py` — scenarios array; optional monthly_investment_override, expense_growth_pct, salary_growth_pct, target_buffer.
- `backend/wealth_stock_service.py` — diversification_explanation, sector_gaps, rebalancing_impact_preview in manager view.
- `backend/wealth_suggestions_service.py` — why_this_matters and destination on each suggestion.
- `backend/main.py` — portfolio endpoint uses include_enrichment=True; projections endpoint accepts optional scenario params.

### Frontend
- `frontend-react/src/components/WealthHubLayout.tsx` — Grouped nav, summary bar.
- `frontend-react/src/components/WealthHubSectionNav.tsx` — **New** grouped section nav.
- `frontend-react/src/components/WealthHubSummaryBar.tsx` — **New** persistent summary bar.
- `frontend-react/src/pages/WealthOverview.tsx` — Uses getWealthOverview; summary strip, alerts, next actions, flow, goal preview, net worth preview.
- `frontend-react/src/pages/WealthCashflow.tsx` — Flow view, ratios, fixed/variable, investable surplus, MoM, mini-suggestions.
- `frontend-react/src/pages/WealthProjections.tsx` — Scenarios, projected guidance, mini-suggestions.
- `frontend-react/src/pages/WealthPortfolio.tsx` — Summary strip (largest/best/worst), allocation by sector, latest transactions, dividend summary, portfolio suggestions, Add to Watchlist in discovery.
- `frontend-react/src/pages/WealthManager.tsx` — Title “Portfolio Intelligence”; diversification explanation, sector gaps, rebalancing impact preview.
- `frontend-react/src/pages/WealthSuggestions.tsx` — why_this_matters, destination link, sort by severity.
- `frontend-react/src/pages/WealthGoals.tsx` — **New** Goals tab (wealth goal types).
- `frontend-react/src/pages/WealthWatchlist.tsx` — **New** Watchlist CRUD.
- `frontend-react/src/pages/WealthNetWorth.tsx` — **New** Net Worth page.
- `frontend-react/src/App.tsx` — Routes for `/wealth/goals`, `/wealth/watchlist`, `/wealth/net-worth`.
- `frontend-react/src/api/client.ts` — Types and calls for overview, score, net worth, watchlist, liabilities; extended CashflowSummary, ProjectionsSummary (scenarios), PortfolioSummary (enrichment), PortfolioManagerView (explanation, sector_gaps, impact), Suggestion (why_this_matters, destination).

---

## New files

- `frontend-react/src/components/WealthHubSectionNav.tsx`
- `frontend-react/src/components/WealthHubSummaryBar.tsx`
- `frontend-react/src/pages/WealthGoals.tsx`
- `frontend-react/src/pages/WealthWatchlist.tsx`
- `frontend-react/src/pages/WealthNetWorth.tsx`
- `WEALTH_HUB_DELIVERY.md` (this file)

(Backend services `wealth_overview_service`, `wealth_score_service`, `wealth_networth_service` and DB watchlist/liabilities were added in the earlier phase.)

---

## DB schema / migrations

- **wealth_liabilities**: Table already added (id, user_id, name, balance, liability_type, notes, updated_at).
- **stock_watchlist**: Existing; migration adds columns if missing: target_buy_price, current_price, sector, notes.
- No breaking changes to existing tables; goals use existing `financial_goals`.

---

## Routes and endpoints

| Route | Description |
|-------|-------------|
| `/wealth/overview` | Overview dashboard (unchanged path) |
| `/wealth/salary` | Income (unchanged) |
| `/wealth/investments` | Investments (unchanged) |
| `/wealth/portfolio` | Portfolio with enrichment (unchanged path) |
| `/wealth/cashflow` | Cashflow with new fields (unchanged) |
| `/wealth/projections` | Projections with scenarios; optional query params (unchanged path) |
| `/wealth/manager` | Portfolio Intelligence (unchanged path; label only renamed) |
| `/wealth/suggestions` | Suggestions with why/destination (unchanged) |
| `/wealth/goals` | **New** Wealth Goals page |
| `/wealth/watchlist` | **New** Watchlist page |
| `/wealth/net-worth` | **New** Net Worth page |

Existing API paths unchanged. New/updated response fields are additive.

---

## Manual test steps

1. **Overview** — Open `/wealth/overview`; confirm summary strip (income, expenses, free cash, invested, portfolio, score), priority alerts, “What should I do next?”, wealth flow links, goal preview, net worth preview.
2. **Portfolio** — Open `/wealth/portfolio`; confirm largest/best/worst strip, allocation by sector, latest transactions, dividend summary (if any), portfolio suggestions; open “Discover stocks”, search, add to watchlist, check affordability.
3. **Cashflow** — Open `/wealth/cashflow`; confirm monthly flow, flow breakdown, ratios, fixed vs variable (if any), investable surplus, MoM comparison, mini-suggestions.
4. **Projections** — Open `/wealth/projections`; confirm main metrics, portfolio projection 6m/1y/3y, scenario comparison (4 scenarios), projected guidance.
5. **Portfolio Intelligence** — Open `/wealth/manager`; confirm title “Portfolio Intelligence”, diversification explanation, sector gaps, rebalancing impact preview (if applicable), stocks that work for you, rebalancing suggestions.
6. **Goals** — Open `/wealth/goals`; create goal (e.g. monthly investment target), list, edit, delete.
7. **Watchlist** — Open `/wealth/watchlist`; add ticker, list, edit, remove; add from Portfolio discovery and confirm it appears.
8. **Net Worth** — Open `/wealth/net-worth`; confirm assets/liabilities/net worth and delta; add liability, edit, delete.
9. **Suggestions** — Open `/wealth/suggestions`; confirm severity order, “why this matters”, and destination links.
10. **Summary bar** — Navigate across Wealth Hub tabs; confirm persistent bar shows income, expenses, free cash, invested, portfolio, Wealth Score.

---

## Follow-up improvements

- **Projections**: Optional form-based scenario controls (monthly investment, expense/salary growth %) in the UI for live recalculation.
- **Net worth**: Optional monthly history and simple chart for net worth trend.
- **Portfolio**: Optional “simulate buy” impact on allocation (e.g. “If you buy 10 AAPL, concentration becomes X%”).
- **Goals**: Deeper integration with Projections (e.g. “At current pace, goal Y will be reached in Z months”).
- **Wealth Score**: Optional drill-down modal for factor breakdown.
- **Code-splitting**: Consider lazy routes for Wealth Hub to reduce initial bundle size.
