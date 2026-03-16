"""
Net worth: assets (free cash, portfolio value, optional other) minus liabilities.
"""
from typing import Dict, Any
from datetime import datetime
import database


def get_net_worth(user_id: str = None, year: int = None, month: int = None) -> Dict[str, Any]:
    """
    Current net worth: assets - liabilities.
    Assets: free_cash (from cashflow) + portfolio_value. Liabilities: sum of wealth_liabilities.
    Optionally return previous month for delta.
    """
    now = datetime.now()
    y = year or now.year
    m = month or now.month
    uid = user_id

    try:
        import wealth_cashflow_service as cf
        import wealth_portfolio_service as ps
        cashflow = cf.get_cashflow_summary(y, m, user_id=uid)
        portfolio = ps.get_portfolio_summary(user_id=uid)
    except Exception:
        cashflow = {}
        portfolio = {}

    free_cash = cashflow.get("free_cash") or 0
    portfolio_value = portfolio.get("total_current_value") or 0
    total_assets = free_cash + portfolio_value

    liabilities_list = database.list_liabilities(user_id=uid)
    total_liabilities = sum(float(l.get("balance") or 0) for l in liabilities_list)

    net_worth = total_assets - total_liabilities

    # Previous month delta (simplified: use same liabilities, previous month cashflow)
    prev_net = None
    if m == 1:
        prev_y, prev_m = y - 1, 12
    else:
        prev_y, prev_m = y, m - 1
    try:
        import wealth_cashflow_service as cf2
        prev_cf = cf2.get_cashflow_summary(prev_y, prev_m, user_id=uid)
        prev_portfolio = portfolio  # same as current for simplicity; could snapshot in future
        prev_assets = (prev_cf.get("free_cash") or 0) + (prev_portfolio.get("total_current_value") or 0)
        prev_net = prev_assets - total_liabilities
    except Exception:
        pass

    delta = (net_worth - prev_net) if prev_net is not None else None

    return {
        "year": y,
        "month": m,
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "net_worth": round(net_worth, 2),
        "assets_breakdown": {
            "free_cash": round(free_cash, 2),
            "portfolio_value": round(portfolio_value, 2),
        },
        "liabilities_count": len(liabilities_list),
        "delta_vs_previous_month": round(delta, 2) if delta is not None else None,
    }
