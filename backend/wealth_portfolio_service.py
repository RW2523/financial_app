"""
Wealth Hub: portfolio holdings computed from investment transactions.
Deterministic: total quantity per ticker, average buy price, total invested, realized/unrealized P&L.
"""
from typing import Dict, List, Any, Optional
from collections import defaultdict
import database


def get_holdings_from_transactions(
    transactions: List[Dict],
    current_prices: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Compute holdings from transaction list. current_prices: { ticker: price } for unrealized P&L.
    Returns list of { ticker, stock_name, quantity, avg_buy_price, total_invested, realized_pnl,
                     current_price, current_value, unrealized_pnl }.
    """
    # FIFO/lot tracking for realized P&L on sells
    lots: List[Dict] = []  # { ticker, qty, price }
    realized_by_ticker: Dict[str, float] = defaultdict(float)
    invested_by_ticker: Dict[str, float] = defaultdict(float)
    qty_by_ticker: Dict[str, float] = defaultdict(float)
    stock_name_by_ticker: Dict[str, str] = {}

    for t in sorted(transactions, key=lambda x: (x["date"], x["id"] or 0)):
        ticker = (t.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        trans_type = (t.get("transaction_type") or "").upper()
        qty = float(t.get("quantity") or 0)
        price = float(t.get("price") or 0)
        fees = float(t.get("fees") or 0)
        if t.get("stock_name"):
            stock_name_by_ticker[ticker] = t["stock_name"]

        if trans_type == "BUY":
            lots.append({"ticker": ticker, "qty": qty, "price": price})
            qty_by_ticker[ticker] += qty
            invested_by_ticker[ticker] += qty * price + fees
        elif trans_type == "SELL":
            remaining = qty
            proceeds = qty * price - fees
            cost_sold = 0.0
            new_lots = []
            for lot in lots:
                if lot["ticker"] != ticker or remaining <= 0:
                    new_lots.append(lot)
                    continue
                sell_from_lot = min(lot["qty"], remaining)
                cost_sold += sell_from_lot * lot["price"]
                remaining -= sell_from_lot
                if lot["qty"] > sell_from_lot:
                    new_lots.append({"ticker": ticker, "qty": lot["qty"] - sell_from_lot, "price": lot["price"]})
            lots = new_lots
            qty_by_ticker[ticker] -= qty
            realized_by_ticker[ticker] += proceeds - cost_sold
            invested_by_ticker[ticker] -= cost_sold
        elif trans_type == "DIVIDEND":
            realized_by_ticker[ticker] += qty * price - fees  # treat dividend as realized income

    out = []
    current_prices = current_prices or {}
    for ticker, qty in qty_by_ticker.items():
        if qty <= 0:
            continue
        invested = invested_by_ticker.get(ticker, 0)
        avg_price = invested / qty if qty else 0
        current_price = current_prices.get(ticker)
        current_value = (current_price * qty) if current_price is not None else None
        unrealized = (current_value - invested) if current_value is not None else None
        out.append({
            "ticker": ticker,
            "stock_name": stock_name_by_ticker.get(ticker) or ticker,
            "quantity": round(qty, 4),
            "avg_buy_price": round(avg_price, 4),
            "total_invested": round(invested, 2),
            "realized_pnl": round(realized_by_ticker.get(ticker, 0), 2),
            "current_price": round(current_price, 4) if current_price is not None else None,
            "current_value": round(current_value, 2) if current_value is not None else None,
            "unrealized_pnl": round(unrealized, 2) if unrealized is not None else None,
        })
    return sorted(out, key=lambda x: -x["total_invested"])


def get_portfolio_summary(
    user_id: str = None,
    current_prices: Optional[Dict[str, float]] = None,
    include_enrichment: bool = False,
) -> Dict[str, Any]:
    """Total portfolio value, total invested, total realized P&L, total unrealized P&L.
    If include_enrichment: add largest_holding, best_performer, worst_performer, allocation_by_sector,
    latest_transactions, dividend_summary."""
    transactions = database.list_investment_transactions(user_id=user_id)
    holdings = get_holdings_from_transactions(transactions, current_prices)
    total_invested = sum(h["total_invested"] for h in holdings)
    total_realized = sum(h["realized_pnl"] for h in holdings)
    total_current = sum(h["current_value"] or h["total_invested"] for h in holdings)
    total_unrealized = sum(
        (h["unrealized_pnl"] if h["unrealized_pnl"] is not None else 0) for h in holdings
    )
    out = {
        "holdings": holdings,
        "total_invested": round(total_invested, 2),
        "total_realized_pnl": round(total_realized, 2),
        "total_current_value": round(total_current, 2),
        "total_unrealized_pnl": round(total_unrealized, 2),
    }
    if include_enrichment:
        _add_portfolio_enrichment(out, holdings, total_current, transactions, user_id)
    return out


def _add_portfolio_enrichment(
    out: Dict[str, Any],
    holdings: List[Dict],
    total_current: float,
    transactions: List[Dict],
    user_id: str = None,
) -> None:
    """Mutate out with largest_holding, best_performer, worst_performer, allocation_by_sector, latest_transactions, dividend_summary."""
    # Largest holding
    if holdings and total_current > 0:
        top = holdings[0]
        top_val = top.get("current_value") or top.get("total_invested") or 0
        out["largest_holding"] = {
            "ticker": top.get("ticker"),
            "value": round(top_val, 2),
            "pct": round((top_val / total_current) * 100, 1),
        }
        # Best / worst by unrealized P&L
        with_pnl = [(h, h.get("unrealized_pnl") if h.get("unrealized_pnl") is not None else 0) for h in holdings]
        with_pnl.sort(key=lambda x: x[1], reverse=True)
        if with_pnl:
            out["best_performer"] = {"ticker": with_pnl[0][0].get("ticker"), "unrealized_pnl": with_pnl[0][1]}
            out["worst_performer"] = {"ticker": with_pnl[-1][0].get("ticker"), "unrealized_pnl": with_pnl[-1][1]}
    else:
        out["largest_holding"] = None
        out["best_performer"] = None
        out["worst_performer"] = None

    # Allocation by sector (from stock service)
    try:
        import wealth_stock_service as wss
        sector_value: Dict[str, float] = {}
        for h in holdings:
            ticker = (h.get("ticker") or "").upper()
            val = h.get("current_value") or h.get("total_invested") or 0
            d = wss.get_stock_details(ticker)
            sec = d.get("sector") or "Other"
            sector_value[sec] = sector_value.get(sec, 0) + val
        out["allocation_by_sector"] = {}
        if total_current > 0:
            for s, v in sector_value.items():
                out["allocation_by_sector"][s] = round((v / total_current) * 100, 1)
    except Exception:
        out["allocation_by_sector"] = {}

    # Latest transactions (last 10)
    sorted_tx = sorted(transactions, key=lambda x: (x.get("date") or "", x.get("id") or 0), reverse=True)
    out["latest_transactions"] = [
        {
            "id": t.get("id"),
            "date": t.get("date"),
            "ticker": t.get("ticker"),
            "transaction_type": t.get("transaction_type"),
            "quantity": t.get("quantity"),
            "price": t.get("price"),
        }
        for t in sorted_tx[:10]
    ]

    # Dividend summary (this year)
    from datetime import datetime
    now = datetime.now()
    y = now.year
    div_total = 0.0
    for t in transactions:
        if (t.get("transaction_type") or "").upper() != "DIVIDEND":
            continue
        if (t.get("date") or "")[:4] != str(y):
            continue
        div_total += float(t.get("quantity") or 0) * float(t.get("price") or 0) - float(t.get("fees") or 0)
    out["dividend_summary"] = {"year": y, "total_dividends": round(div_total, 2)}
