"""
Wealth Hub: stock search/details with mock or live provider (yfinance).
Set STOCK_PROVIDER=yfinance or yahoo to fetch real-time/delayed prices from Yahoo Finance.
Without it, uses static mock data (no API key required).
"""
from typing import Dict, Any, Optional

# Mock data for demo when no provider is configured (multiple sectors for diversification)
_MOCK_STOCKS = {
    "AAPL": {"name": "Apple Inc.", "sector": "Technology", "price": 185.0, "change": 1.2, "market_cap": "2.9T", "pe": 29.5, "dividend_yield": 0.52, "range_52w": "164–199"},
    "GOOGL": {"name": "Alphabet Inc.", "sector": "Technology", "price": 140.0, "change": -0.5, "market_cap": "1.8T", "pe": 25.0, "dividend_yield": 0.50, "range_52w": "125–155"},
    "MSFT": {"name": "Microsoft Corporation", "sector": "Technology", "price": 410.0, "change": 0.8, "market_cap": "3.0T", "pe": 36.0, "dividend_yield": 0.72, "range_52w": "380–430"},
    "AMZN": {"name": "Amazon.com Inc.", "sector": "Consumer Cyclical", "price": 178.0, "change": -0.3, "market_cap": "1.9T", "pe": 78.0, "dividend_yield": 0.0, "range_52w": "165–195"},
    "META": {"name": "Meta Platforms Inc.", "sector": "Technology", "price": 485.0, "change": 1.5, "market_cap": "1.2T", "pe": 28.0, "dividend_yield": 0.42, "range_52w": "440–535"},
    "JPM": {"name": "JPMorgan Chase & Co.", "sector": "Financials", "price": 198.0, "change": 0.4, "market_cap": "570B", "pe": 11.0, "dividend_yield": 2.2, "range_52w": "170–210"},
    "V": {"name": "Visa Inc.", "sector": "Financials", "price": 278.0, "change": -0.2, "market_cap": "570B", "pe": 31.0, "dividend_yield": 0.8, "range_52w": "250–300"},
    "JNJ": {"name": "Johnson & Johnson", "sector": "Healthcare", "price": 158.0, "change": 0.3, "market_cap": "380B", "pe": 15.0, "dividend_yield": 3.2, "range_52w": "145–175"},
    "UNH": {"name": "UnitedHealth Group", "sector": "Healthcare", "price": 525.0, "change": -0.5, "market_cap": "485B", "pe": 24.0, "dividend_yield": 1.5, "range_52w": "480–560"},
    "XOM": {"name": "Exxon Mobil Corp.", "sector": "Energy", "price": 118.0, "change": 0.8, "market_cap": "470B", "pe": 12.0, "dividend_yield": 3.4, "range_52w": "95–125"},
    "PG": {"name": "Procter & Gamble", "sector": "Consumer Defensive", "price": 168.0, "change": 0.2, "market_cap": "395B", "pe": 26.0, "dividend_yield": 2.5, "range_52w": "155–180"},
    "KO": {"name": "Coca-Cola Co.", "sector": "Consumer Defensive", "price": 62.0, "change": -0.1, "market_cap": "268B", "pe": 22.0, "dividend_yield": 3.1, "range_52w": "55–68"},
    "VZ": {"name": "Verizon Communications", "sector": "Communication", "price": 40.0, "change": 0.5, "market_cap": "168B", "pe": 9.0, "dividend_yield": 6.5, "range_52w": "36–44"},
    "DIS": {"name": "Walt Disney Co.", "sector": "Communication", "price": 112.0, "change": -0.4, "market_cap": "205B", "pe": 68.0, "dividend_yield": 0.3, "range_52w": "85–125"},
}


def _get_live_provider() -> str:
    """Return STOCK_PROVIDER env (e.g. 'yfinance' or 'yahoo') if set and live fetch is enabled."""
    try:
        import os
        p = (os.environ.get("STOCK_PROVIDER") or "").strip().lower()
        if p in ("yfinance", "yahoo"):
            return p
    except Exception:
        pass
    return ""


def _fetch_live_details(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Fetch current price and details from Yahoo Finance via yfinance (if installed).
    Returns dict with current_price, stock_name, sector, change, etc., or None on failure.
    """
    provider = _get_live_provider()
    if not provider:
        return None
    try:
        import yfinance as yf
    except ImportError:
        return None
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return None
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        # Current price: prefer regularMarketPrice/currentPrice, else fast_info.lastPrice, else last Close
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        if price is None:
            try:
                fi = getattr(t, "fast_info", None)
                if fi is not None:
                    price = getattr(fi, "last_price", None)
            except Exception:
                pass
        if price is None:
            hist = t.history(period="5d")
            if hist is not None and not hist.empty and "Close" in hist.columns:
                price = float(hist["Close"].iloc[-1])
        if price is None:
            return None
        price = float(price)
        # Optional: previous close for % change
        prev = info.get("previousClose") or info.get("regularMarketPreviousClose")
        change = None
        if prev is not None and prev != 0:
            change = round(((price - float(prev)) / float(prev)) * 100, 2)
        return {
            "ticker": ticker,
            "stock_name": info.get("shortName") or info.get("longName") or ticker,
            "sector": info.get("sector") or (ticker in _MOCK_STOCKS and _MOCK_STOCKS[ticker].get("sector")) or None,
            "current_price": round(price, 4),
            "change": change,
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
            "dividend_yield": info.get("yield") or info.get("dividendYield"),
            "range_52w": info.get("fiftyTwoWeekHigh") and info.get("fiftyTwoWeekLow") and f"{info['fiftyTwoWeekLow']}–{info['fiftyTwoWeekHigh']}" or None,
            "source": "live",
        }
    except Exception:
        return None


def get_stock_details(ticker: str) -> Dict[str, Any]:
    """
    Return stock details. Uses live provider (yfinance) if STOCK_PROVIDER=yfinance or yahoo, else mock.
    Shape: ticker, stock_name, sector, current_price, change, market_cap, pe_ratio, dividend_yield, range_52w, source.
    """
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return _empty_details(ticker or "?", "manual")

    # Try live provider first when enabled
    live = _fetch_live_details(ticker)
    if live is not None and live.get("current_price") is not None:
        return {**_empty_details(ticker, "live"), **{k: v for k, v in live.items() if v is not None}}

    # Fallback: mock or manual
    mock = _MOCK_STOCKS.get(ticker)
    if mock:
        return {
            "ticker": ticker,
            "stock_name": mock.get("name"),
            "sector": mock.get("sector"),
            "current_price": mock.get("price"),
            "change": mock.get("change"),
            "market_cap": mock.get("market_cap"),
            "pe_ratio": mock.get("pe"),
            "dividend_yield": mock.get("dividend_yield"),
            "range_52w": mock.get("range_52w"),
            "source": "mock",
        }
    return _empty_details(ticker, "manual")


def _empty_details(ticker: str, source: str) -> Dict[str, Any]:
    return {
        "ticker": ticker,
        "stock_name": None,
        "sector": None,
        "current_price": None,
        "change": None,
        "market_cap": None,
        "pe_ratio": None,
        "dividend_yield": None,
        "range_52w": None,
        "source": source,
    }


def search_stocks(query: str = "") -> list:
    """
    Search/list stocks. Optional query filters by ticker or name (case-insensitive).
    Returns list of stock details (same shape as get_stock_details).
    """
    q = (query or "").strip().upper()
    out = []
    for ticker, mock in _MOCK_STOCKS.items():
        if not q or q in ticker or (mock.get("name") and q in (mock.get("name") or "").upper()):
            out.append({
                "ticker": ticker,
                "stock_name": mock.get("name"),
                "sector": mock.get("sector"),
                "current_price": mock.get("price"),
                "change": mock.get("change"),
                "market_cap": mock.get("market_cap"),
                "pe_ratio": mock.get("pe"),
                "dividend_yield": mock.get("dividend_yield"),
                "range_52w": mock.get("range_52w"),
                "source": "mock",
            })
    return sorted(out, key=lambda x: (x["ticker"]))


def get_diversification_suggestions(user_id: str = None) -> Dict[str, Any]:
    """
    Best stocks for your case: you're concentrated in one sector/ticker.
    Returns stocks from sectors you don't hold (or hold less), to diversify.
    """
    import wealth_portfolio_service as ps
    portfolio = ps.get_portfolio_summary(user_id=user_id)
    holdings = portfolio.get("holdings") or []
    your_tickers = {(h.get("ticker") or "").upper() for h in holdings}
    your_sectors = set()
    for h in holdings:
        ticker = (h.get("ticker") or "").upper()
        d = get_stock_details(ticker)
        if d.get("sector"):
            your_sectors.add(d["sector"])

    # Suggest stocks from sectors you don't have, or other tickers in same sector to spread
    suggestions = []
    for ticker, mock in _MOCK_STOCKS.items():
        if ticker in your_tickers:
            continue
        sector = mock.get("sector") or "Other"
        reason = "Different sector (diversify)" if sector not in your_sectors else "Same sector, different company"
        suggestions.append({
            "ticker": ticker,
            "stock_name": mock.get("name"),
            "sector": sector,
            "current_price": mock.get("price"),
            "change": mock.get("change"),
            "market_cap": mock.get("market_cap"),
            "pe_ratio": mock.get("pe"),
            "dividend_yield": mock.get("dividend_yield"),
            "range_52w": mock.get("range_52w"),
            "reason": reason,
        })
    # Prefer different sectors first, then by dividend (income) then by market cap
    suggestions.sort(key=lambda x: (
        0 if x["sector"] not in your_sectors else 1,
      -(x["dividend_yield"] or 0),
      x["ticker"],
    ))
    return {
        "your_holdings": list(your_tickers),
        "your_sectors": list(your_sectors),
        "suggestions": suggestions[:15],
    }


def get_portfolio_manager_view(user_id: str = None) -> Dict[str, Any]:
    """
    Portfolio Manager: allocation by sector, diversification score, stocks that work for you, rebalancing hints.
    """
    import wealth_portfolio_service as ps
    portfolio = ps.get_portfolio_summary(user_id=user_id)
    holdings = portfolio.get("holdings") or []
    total_value = portfolio.get("total_current_value") or 0

    # Allocation by sector
    sector_value: Dict[str, float] = {}
    for h in holdings:
        ticker = (h.get("ticker") or "").upper()
        value = h.get("current_value") or h.get("total_invested") or 0
        d = get_stock_details(ticker)
        sector = d.get("sector") or "Other"
        sector_value[sector] = sector_value.get(sector, 0) + value

    allocation_by_sector = {}
    if total_value > 0:
        for s, v in sector_value.items():
            allocation_by_sector[s] = round((v / total_value) * 100, 1)
    else:
        allocation_by_sector = {s: 0.0 for s in sector_value}

    # Diversification score 0–100: penalize single-stock/single-sector concentration
    max_sector_pct = max(allocation_by_sector.values()) if allocation_by_sector else 100
    num_sectors = len([v for v in allocation_by_sector.values() if v > 0])
    # Score: more sectors = higher; lower max concentration = higher
    diversification_score = min(100, round(num_sectors * 15 + (100 - max_sector_pct) * 0.5, 0)) if (num_sectors or max_sector_pct < 100) else 0
    diversification_score = max(0, min(100, diversification_score))

    # Stocks that work for you (top picks from diversification)
    div = get_diversification_suggestions(user_id=user_id)
    stocks_that_work_for_you = []
    for s in (div.get("suggestions") or [])[:10]:
        why = "Diversify into a new sector" if (s.get("reason") or "").startswith("Different") else "Add exposure in your sector"
        if s.get("dividend_yield") and s.get("dividend_yield") >= 2:
            why += " · Good for income"
        stocks_that_work_for_you.append({
            "ticker": s.get("ticker"),
            "stock_name": s.get("stock_name"),
            "sector": s.get("sector"),
            "current_price": s.get("current_price"),
            "dividend_yield": s.get("dividend_yield"),
            "why_for_you": why,
        })

    # Rebalancing: sectors you have 0% in (from universe)
    all_sectors = set()
    for mock in _MOCK_STOCKS.values():
        if mock.get("sector"):
            all_sectors.add(mock["sector"])
    your_sectors = {k for k, v in allocation_by_sector.items() if v > 0}
    missing_sectors = sorted(all_sectors - your_sectors)
    rebalancing_suggestions = []
    for sec in missing_sectors:
        # One top pick for this sector (by dividend then first ticker)
        picks = [t for t, m in _MOCK_STOCKS.items() if m.get("sector") == sec]
        if picks:
            best = min(picks, key=lambda t: (-(_MOCK_STOCKS[t].get("dividend_yield") or 0), t))
            rebalancing_suggestions.append({
                "sector": sec,
                "suggestion": f"Consider adding {sec}",
                "top_pick": best,
                "top_pick_name": _MOCK_STOCKS[best].get("name"),
                "price": _MOCK_STOCKS[best].get("price"),
            })

    # Diversification explanation (why score is what it is)
    factors = []
    if num_sectors == 0:
        factors.append("No holdings; add investments to build diversification.")
    else:
        if num_sectors >= 4:
            factors.append(f"You hold {num_sectors} sectors (good spread).")
        elif num_sectors >= 2:
            factors.append(f"You hold {num_sectors} sectors; adding more sectors can improve the score.")
        else:
            factors.append(f"Only {num_sectors} sector(s); concentration in one sector lowers the score.")
        if max_sector_pct > 70:
            factors.append(f"Largest sector is {max_sector_pct:.0f}% of portfolio (high concentration).")
        elif max_sector_pct > 50:
            factors.append(f"Largest sector is {max_sector_pct:.0f}% (moderate concentration).")
        if len(holdings) < 3 and len(holdings) > 0:
            factors.append(f"Low number of holdings ({len(holdings)}) increases single-stock risk.")
    diversification_explanation = " ".join(factors) if factors else "Diversification score based on sector spread and concentration."

    # Sector gap analysis: sectors not represented
    all_sectors = set()
    for mock in _MOCK_STOCKS.values():
        if mock.get("sector"):
            all_sectors.add(mock["sector"])
    sector_gaps = sorted(all_sectors - your_sectors) if total_value > 0 else list(all_sectors)

    # Rebalancing impact preview: adding one holding in an uncovered sector could improve score
    impact_preview = None
    current_score = int(diversification_score)
    if sector_gaps and num_sectors < len(all_sectors):
        # Simulate: add one sector -> num_sectors+1, max_sector might drop if new sector takes 20%
        new_num = num_sectors + 1
        new_max = max(max_sector_pct * 0.8, 50)  # rough: new sector reduces top
        potential_score = min(100, round(new_num * 15 + (100 - new_max) * 0.5, 0))
        if potential_score > current_score:
            impact_preview = {
                "current_score": current_score,
                "potential_score": int(potential_score),
                "message": f"Adding exposure to a missing sector (e.g. {sector_gaps[0]}) could improve diversification score from {current_score} to ~{potential_score}.",
            }

    return {
        "total_portfolio_value": round(total_value, 2),
        "allocation_by_sector": allocation_by_sector,
        "diversification_score": current_score,
        "diversification_explanation": diversification_explanation,
        "sector_gaps": sector_gaps,
        "rebalancing_impact_preview": impact_preview,
        "stocks_that_work_for_you": stocks_that_work_for_you,
        "rebalancing_suggestions": rebalancing_suggestions,
        "your_holdings_count": len(holdings),
        "sectors_held": list(your_sectors) if total_value > 0 else [],
    }


def get_current_prices_for_tickers(tickers: list) -> Dict[str, float]:
    """Return { ticker: price } for portfolio unrealized P&L. Uses mock/provider."""
    out = {}
    for t in tickers:
        t = (t or "").strip().upper()
        if not t:
            continue
        details = get_stock_details(t)
        if details.get("current_price") is not None:
            out[t] = float(details["current_price"])
    return out


def check_stock_affordability(
    ticker: str,
    quantity: float,
    price_per_share: float,
    user_id: str = None,
) -> Dict[str, Any]:
    """
    Can I buy this stock? Uses free_cash, this month income/expenses, allocation, concentration.
    Returns: affordable, message, free_cash, cost, concentration_risk, reasons.
    """
    from datetime import datetime
    import wealth_cashflow_service as cf
    import wealth_portfolio_service as ps

    ticker = (ticker or "").strip().upper()
    cost = float(quantity or 0) * float(price_per_share or 0)
    reasons = []

    cashflow = cf.get_cashflow_summary(user_id=user_id)
    free_cash = cashflow.get("free_cash") or 0
    total_income = cashflow.get("total_income") or 0

    portfolio = ps.get_portfolio_summary(user_id=user_id)
    holdings = portfolio.get("holdings") or []
    total_value = portfolio.get("total_current_value") or 0

    # Concentration: after this buy, would this ticker be > 50%?
    current_holding_value = next((h.get("current_value") or h.get("total_invested") or 0 for h in holdings if (h.get("ticker") or "").upper() == ticker), 0)
    new_value = current_holding_value + cost
    new_total = total_value + cost
    concentration_pct = (new_value / new_total * 100) if new_total > 0 else (100 if cost > 0 else 0)
    concentration_risk = concentration_pct > 50

    if concentration_risk:
        reasons.append(f"Adding this would make {ticker} {concentration_pct:.1f}% of your portfolio (concentration risk).")

    if cost <= 0:
        return {
            "affordable": True,
            "message": "No cost; no purchase.",
            "free_cash": round(free_cash, 2),
            "cost": 0,
            "concentration_risk": False,
            "reasons": [],
        }

    if free_cash < cost:
        reasons.append(f"Free cash ({free_cash:.2f}) is below purchase cost ({cost:.2f}).")
    if total_income > 0 and cost > total_income * 0.5:
        reasons.append(f"Purchase cost is more than 50% of this month's income.")

    affordable = free_cash >= cost and not (concentration_risk and free_cash < cost * 1.2)
    if free_cash >= cost and not concentration_risk:
        message = "Affordable within current surplus."
    elif free_cash >= cost and concentration_risk:
        message = "Affordable but would increase concentration risk in this stock."
    else:
        message = "Would reduce free cash too much; consider a smaller amount or waiting."

    return {
        "affordable": affordable,
        "message": message,
        "free_cash": round(free_cash, 2),
        "cost": round(cost, 2),
        "concentration_risk": concentration_risk,
        "reasons": reasons,
    }
