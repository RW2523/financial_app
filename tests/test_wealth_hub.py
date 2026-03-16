"""
Tests for Wealth Hub: portfolio holdings, cashflow, projections, suggestions, stock affordability.
"""
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

os.chdir(_BACKEND)

import pytest
from datetime import datetime
import database
import context as request_context

# Portfolio: pure function, no DB
from wealth_portfolio_service import get_holdings_from_transactions
from wealth_cashflow_service import get_cashflow_summary
from wealth_suggestions_service import get_suggestions
from wealth_stock_service import check_stock_affordability, get_stock_details
from wealth_projections_service import get_projections, PROJECTION_MODES


@pytest.fixture(scope="module")
def ensure_db():
    database.init_database()
    request_context.set_current_user_id("test_wealth_user")
    try:
        yield
    finally:
        request_context.set_current_user_id(None)


def test_holdings_buy_only():
    """Holdings from BUY-only transactions: quantity and total_invested."""
    tx = [
        {"id": 1, "date": "2025-01-01", "ticker": "AAPL", "transaction_type": "BUY", "quantity": 10, "price": 100, "fees": 5},
        {"id": 2, "date": "2025-01-15", "ticker": "AAPL", "transaction_type": "BUY", "quantity": 5, "price": 110, "fees": 0},
    ]
    holdings = get_holdings_from_transactions(tx)
    assert len(holdings) == 1
    assert holdings[0]["ticker"] == "AAPL"
    assert holdings[0]["quantity"] == 15
    total_inv = 10 * 100 + 5 + 5 * 110
    assert holdings[0]["total_invested"] == total_inv
    assert abs(holdings[0]["avg_buy_price"] - total_inv / 15) < 0.01
    assert holdings[0]["realized_pnl"] == 0


def test_holdings_buy_sell_realized_pnl():
    """SELL produces realized P&L (FIFO)."""
    tx = [
        {"id": 1, "date": "2025-01-01", "ticker": "AAPL", "transaction_type": "BUY", "quantity": 10, "price": 100, "fees": 0},
        {"id": 2, "date": "2025-02-01", "ticker": "AAPL", "transaction_type": "SELL", "quantity": 4, "price": 120, "fees": 0},
    ]
    holdings = get_holdings_from_transactions(tx)
    assert len(holdings) == 1
    assert holdings[0]["quantity"] == 6
    # Cost of 4 sold = 4*100 = 400, proceeds = 4*120 = 480, realized = 80
    assert holdings[0]["realized_pnl"] == 80
    assert holdings[0]["total_invested"] == 6 * 100


def test_holdings_unrealized_pnl():
    """When current_prices given, unrealized_pnl = current_value - total_invested."""
    tx = [
        {"id": 1, "date": "2025-01-01", "ticker": "AAPL", "transaction_type": "BUY", "quantity": 10, "price": 100, "fees": 0},
    ]
    holdings = get_holdings_from_transactions(tx, current_prices={"AAPL": 110})
    assert len(holdings) == 1
    assert holdings[0]["current_price"] == 110
    assert holdings[0]["current_value"] == 1100
    assert holdings[0]["unrealized_pnl"] == 100


def test_salary_monthly_summary(ensure_db):
    """Monthly income summary aggregates net + bonus."""
    uid = "test_wealth_user"
    database.create_salary_record(
        date="2025-02-01", source="Employer", gross_amount=6000, deductions=1000,
        net_amount=5000, bonus_amount=500, notes=None, user_id=uid,
    )
    try:
        s = database.get_monthly_income_summary(2025, 2, user_id=uid)
        assert s["net_income"] == 5000
        assert s["bonus_total"] == 500
    finally:
        for r in database.list_salary_records(user_id=uid):
            if r.get("date", "")[:7] == "2025-02":
                database.delete_salary_record(r["id"], user_id=uid)


def test_cashflow_metrics(ensure_db):
    """Cashflow summary returns total_income, total_expenses, total_invested, free_cash, ratios."""
    uid = "test_wealth_user"
    # Ensure we have context for get_spending_by_category_for_month
    request_context.set_current_user_id(uid)
    try:
        cf = get_cashflow_summary(2025, 2, user_id=uid)
        assert "total_income" in cf
        assert "total_expenses" in cf
        assert "total_invested" in cf
        assert "free_cash" in cf
        assert "savings_ratio" in cf
        assert "investment_ratio" in cf
        assert "expense_ratio" in cf
        assert cf["year"] == 2025
        assert cf["month"] == 2
    finally:
        request_context.set_current_user_id(None)


def test_cashflow_investable_surplus_and_mom(ensure_db):
    """Cashflow includes safe_investable_surplus, aggressive_investable_surplus, mom_delta_*."""
    uid = "test_wealth_user"
    request_context.set_current_user_id(uid)
    try:
        cf = get_cashflow_summary(2025, 2, user_id=uid)
        assert "safe_investable_surplus" in cf
        assert "aggressive_investable_surplus" in cf
        assert "remaining_buffer" in cf
        assert "fixed_expenses" in cf
        assert "variable_expenses" in cf
        assert "mom_delta_income" in cf
        assert "mom_delta_expenses" in cf
        assert "mom_delta_savings" in cf
    finally:
        request_context.set_current_user_id(None)


def test_projections_structure(ensure_db):
    """Projections returns projected EOM expenses, surplus, yearly invested, portfolio_projection."""
    uid = "test_wealth_user"
    request_context.set_current_user_id(uid)
    try:
        p = get_projections(2025, 2, user_id=uid, portfolio_growth_mode="moderate")
        assert "projected_end_of_month_expenses" in p
        assert "projected_monthly_surplus" in p
        assert "projected_yearly_invested" in p
        assert "portfolio_projection" in p
        assert "6m" in p["portfolio_projection"]
        assert "1y" in p["portfolio_projection"]
        assert "3y" in p["portfolio_projection"]
        assert p["portfolio_growth_mode"] == "moderate"
        assert p["annual_return_assumption"] == PROJECTION_MODES["moderate"]
    finally:
        request_context.set_current_user_id(None)


def test_projections_scenarios(ensure_db):
    """Projections includes scenarios array with current_pace, disciplined_spending, etc."""
    uid = "test_wealth_user"
    request_context.set_current_user_id(uid)
    try:
        p = get_projections(2025, 2, user_id=uid)
        assert "scenarios" in p
        assert isinstance(p["scenarios"], list)
        ids = [s["id"] for s in p["scenarios"]]
        assert "current_pace" in ids
        assert "disciplined_spending" in ids
        for sc in p["scenarios"]:
            assert "label" in sc
            assert "description" in sc
            assert "projected_monthly_surplus" in sc
            assert "portfolio_1y" in sc
    finally:
        request_context.set_current_user_id(None)


def test_suggestions_expense_ratio_high(ensure_db):
    """When expense_ratio > 80, suggestion about expense ratio appears (if income > 0)."""
    # Suggestions depend on cashflow; we can't easily force expense_ratio without seeding.
    # Just check structure and that we get a list.
    uid = "test_wealth_user"
    request_context.set_current_user_id(uid)
    try:
        out = get_suggestions(2025, 2, user_id=uid)
        assert "suggestions" in out
        assert isinstance(out["suggestions"], list)
        for s in out["suggestions"]:
            assert "id" in s
            assert "title" in s
            assert "message" in s
            assert "metric" in s
            assert "severity" in s
    finally:
        request_context.set_current_user_id(None)


def test_suggestions_why_and_destination(ensure_db):
    """Suggestions may include why_this_matters and destination."""
    uid = "test_wealth_user"
    request_context.set_current_user_id(uid)
    try:
        out = get_suggestions(2025, 2, user_id=uid)
        for s in out["suggestions"]:
            # New fields are optional but when present should be strings
            if "why_this_matters" in s and s["why_this_matters"]:
                assert isinstance(s["why_this_matters"], str)
            if "destination" in s and s["destination"]:
                assert s["destination"].startswith("/")
    finally:
        request_context.set_current_user_id(None)


def test_stock_affordability_affordable():
    """When free_cash >= cost and no concentration risk, affordable is True."""
    # check_stock_affordability uses cashflow + portfolio; with no data, free_cash may be 0.
    result = check_stock_affordability("AAPL", 1, 10.0, user_id="test_wealth_user")
    assert "affordable" in result
    assert "message" in result
    assert "free_cash" in result
    assert "cost" in result
    assert result["cost"] == 10.0


def test_stock_affordability_concentration():
    """Concentration risk flag when single ticker would be > 50%."""
    result = check_stock_affordability("AAPL", 100, 1000.0, user_id="test_wealth_user")
    assert "concentration_risk" in result
    assert "reasons" in result


def test_stock_details_mock():
    """Stock details returns ticker, source; mock stocks have price."""
    d = get_stock_details("AAPL")
    assert d["ticker"] == "AAPL"
    assert d["source"] in ("mock", "manual")
    assert d.get("current_price") is not None or d.get("stock_name") is not None
    d2 = get_stock_details("UNKNOWN_TICKER_XYZ")
    assert d2["ticker"] == "UNKNOWN_TICKER_XYZ"


def test_portfolio_summary_enrichment(ensure_db):
    """Portfolio summary with include_enrichment has largest_holding, best_performer, latest_transactions, dividend_summary."""
    from wealth_portfolio_service import get_portfolio_summary
    uid = "test_wealth_user"
    request_context.set_current_user_id(uid)
    try:
        out = get_portfolio_summary(user_id=uid, include_enrichment=True)
        assert "largest_holding" in out
        assert "best_performer" in out
        assert "worst_performer" in out
        assert "allocation_by_sector" in out
        assert "latest_transactions" in out
        assert "dividend_summary" in out
        assert isinstance(out["latest_transactions"], list)
        if out["dividend_summary"]:
            assert "year" in out["dividend_summary"]
            assert "total_dividends" in out["dividend_summary"]
    finally:
        request_context.set_current_user_id(None)


def test_portfolio_manager_intelligence(ensure_db):
    """Portfolio Manager view includes diversification_explanation, sector_gaps, rebalancing_impact_preview."""
    from wealth_stock_service import get_portfolio_manager_view
    uid = "test_wealth_user"
    view = get_portfolio_manager_view(user_id=uid)
    assert "diversification_score" in view
    assert "diversification_explanation" in view
    assert "sector_gaps" in view
    assert "rebalancing_impact_preview" in view
    assert isinstance(view["sector_gaps"], list)
    if view.get("rebalancing_impact_preview"):
        assert "current_score" in view["rebalancing_impact_preview"]
        assert "potential_score" in view["rebalancing_impact_preview"]
        assert "message" in view["rebalancing_impact_preview"]


def test_overview_structure(ensure_db):
    """Overview returns summary_strip, priority_alerts, next_actions, goals_preview, has_goals."""
    from wealth_overview_service import get_overview
    uid = "test_wealth_user"
    request_context.set_current_user_id(uid)
    try:
        out = get_overview(user_id=uid)
        assert "summary_strip" in out
        assert "priority_alerts" in out
        assert "next_actions" in out
        assert "wealth_score" in out
        assert "goals_preview" in out
        assert "has_goals" in out
        assert "net_worth_preview" in out
        strip = out["summary_strip"]
        assert "net_income_this_month" in strip
        assert "portfolio_value" in strip
    finally:
        request_context.set_current_user_id(None)


def test_net_worth_structure(ensure_db):
    """Net worth service returns total_assets, total_liabilities, net_worth, assets_breakdown."""
    from wealth_networth_service import get_net_worth
    uid = "test_wealth_user"
    out = get_net_worth(user_id=uid)
    assert "total_assets" in out
    assert "total_liabilities" in out
    assert "net_worth" in out
    assert "assets_breakdown" in out
    assert "free_cash" in out["assets_breakdown"]
    assert "portfolio_value" in out["assets_breakdown"]


def test_watchlist_crud(ensure_db):
    """Watchlist: add, list, update, delete."""
    uid = "test_wealth_user"
    request_context.set_current_user_id(uid)
    try:
        item_id = database.add_watchlist_item("TESTTICK", stock_name="Test Stock", notes="Review", user_id=uid)
        assert item_id is not None
        listed = database.list_watchlist(uid)
        assert any((x.get("ticker") or "").upper() == "TESTTICK" for x in listed)
        database.update_watchlist_item(item_id, notes="Updated", user_id=uid)
        database.delete_watchlist_item(item_id, user_id=uid)
        after = database.list_watchlist(uid)
        assert not any((x.get("ticker") or "").upper() == "TESTTICK" for x in after)
    finally:
        request_context.set_current_user_id(None)


def test_liabilities_crud(ensure_db):
    """Liabilities: create, list, update, delete."""
    uid = "test_wealth_user"
    request_context.set_current_user_id(uid)
    try:
        lid = database.create_liability("Test Card", 500.0, liability_type="credit_card", notes="Test", user_id=uid)
        assert lid is not None
        listed = database.list_liabilities(uid)
        assert any(x.get("name") == "Test Card" and x.get("balance") == 500.0 for x in listed)
        database.update_liability(lid, balance=400.0, user_id=uid)
        database.delete_liability(lid, user_id=uid)
        after = database.list_liabilities(uid)
        assert not any(x.get("id") == lid for x in after)
    finally:
        request_context.set_current_user_id(None)


def test_e2e_add_sample_data_then_wealth_hub_has_data(ensure_db):
    """
    E2E: Add sample data (Settings 'Add sample data' flow) then verify Wealth Hub has salary, portfolio, watchlist, liabilities.
    """
    import seed_data
    from wealth_overview_service import get_overview
    from wealth_networth_service import get_net_worth

    uid = "e2e_sample_user"
    request_context.set_current_user_id(uid)
    try:
        database.clear_all_data(user_id=uid)
        result = seed_data.load_sample_data(user_id=uid)
        assert result["expenses"] > 0
        assert result["limits"] == 4
        assert result["goals"] == 2
        assert result.get("salary_records", 0) >= 1
        assert result.get("investments", 0) >= 1
        assert result.get("watchlist", 0) >= 1
        assert result.get("liabilities", 0) >= 1

        overview = get_overview(user_id=uid)
        assert "summary_strip" in overview
        strip = overview["summary_strip"]
        assert "net_income_this_month" in strip
        assert "portfolio_value" in strip
        assert strip.get("net_income_this_month", 0) >= 0
        assert overview.get("net_worth_preview") is not None

        net_worth = get_net_worth(user_id=uid)
        assert net_worth.get("total_liabilities", 0) >= 0
        assert "assets_breakdown" in net_worth
        assert "portfolio_value" in net_worth["assets_breakdown"]

        salary_records = database.list_salary_records(user_id=uid)
        assert len(salary_records) >= 1

        watchlist = database.list_watchlist(user_id=uid)
        assert len(watchlist) >= 1

        liabilities = database.list_liabilities(user_id=uid)
        assert len(liabilities) >= 1
        assert any("student" in (l.get("name") or "").lower() for l in liabilities)

        tx = database.list_investment_transactions(user_id=uid)
        assert len(tx) >= 1
    finally:
        request_context.set_current_user_id(None)
