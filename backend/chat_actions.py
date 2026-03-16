"""
Chat action layer: parse user intents and execute app actions (limits, goals, affordability,
forecast, alerts, Gmail, clear/seed data, help). Used by chat_service for a flexible assistant.
"""
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Categories we accept for limits
LIMIT_CATEGORIES = {
    "food", "transport", "shopping", "entertainment", "utilities", "healthcare", "other", "total",
}


def parse_action(message: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Detect if the message is an action request (not expense add, not plain question).
    Returns (intent, params) or None if not an action.
    """
    if not message or len(message.strip()) < 2:
        return None
    msg = message.strip().lower()
    # --- Help / capabilities ---
    if re.search(r"\b(help|what can you do|what are you|capabilities|what do you support)\b", msg):
        return ("help", {})
    # --- General / greeting ---
    if re.search(r"^(hi|hello|hey|howdy|good\s+(morning|afternoon|evening)|hi there)\b", msg) or msg.strip() in ("hi", "hello", "hey"):
        return ("general", {"greeting": True})
    # --- Set limit: "set food limit to 500", "limit for transport $200" ---
    set_limit_m = re.search(
        r"\b(?:set|put|make)\s+(?:monthly\s+)?(?:limit\s+)?(?:for\s+)?(\w+)\s+(?:to|at|=\s*)\s*\$?\s*([\d,.]+)",
        msg,
        re.I,
    )
    if set_limit_m:
        cat = set_limit_m.group(1).strip().lower()
        if cat in LIMIT_CATEGORIES or cat in ("food", "transport", "shopping", "entertainment", "utilities", "healthcare", "other", "total"):
            amt = float(set_limit_m.group(2).replace(",", ""))
            if amt > 0:
                return ("set_limit", {"category": cat if cat in LIMIT_CATEGORIES else cat, "amount": amt})
    m2 = re.search(r"\blimit\s+(?:for\s+)?(\w+)\s+(?:to\s+)?\$?\s*([\d,.]+)", msg, re.I)
    if m2:
        cat = m2.group(1).strip().lower()
        amt = float(m2.group(2).replace(",", ""))
        if amt > 0 and (cat in LIMIT_CATEGORIES or len(cat) <= 20):
            return ("set_limit", {"category": cat, "amount": amt})
    # --- Delete limit ---
    del_m = re.search(r"\b(?:remove|delete|clear)\s+(?:the\s+)?(?:limit\s+)?(?:for\s+)?(\w+)\b", msg, re.I)
    if del_m and "limit" in msg:
        return ("delete_limit", {"category": del_m.group(1).strip().lower()})
    # --- List limits ---
    if re.search(r"\b(my|show|list|get)\s+limits\b", msg) or re.search(r"\bwhat\s+are\s+my\s+limits\b", msg):
        return ("list_limits", {})
    # --- List goals ---
    if re.search(r"\b(my|show|list|get)\s+goals\b", msg) or re.search(r"\bwhat\s+are\s+my\s+goals\b", msg):
        return ("list_goals", {})
    # --- Create goal (simple): "add goal save 5000 by end of year", "goal: save 2000" ---
    if re.search(r"\b(add|create|set)\s+(?:a\s+)?goal\b", msg, re.I):
        # Try to extract amount and optional date
        am = re.search(r"\b(?:save|savings?)\s*\$?\s*([\d,.]+)", msg, re.I)
        amount = float(am.group(1).replace(",", "")) if am else 1000.0
        target_date = None
        yd = re.search(r"\b(?:by\s+)?(?:end\s+of\s+)?(\d{4})\b", msg)
        if yd:
            target_date = f"{int(yd.group(1))}-12-31"
        return ("create_goal", {"target_amount": amount, "current_amount": 0, "target_date": target_date, "goal_type": "savings_target"})
    # --- Affordability: "can I afford 50", "afford $100 for dinner" ---
    aff_m = re.search(r"\b(?:can i\s+)?afford\s+\$?\s*([\d,.]+)", msg, re.I)
    if aff_m:
        amount = float(aff_m.group(1).replace(",", ""))
        cat = None
        for c in ("food", "transport", "shopping", "entertainment", "dinner", "lunch", "groceries"):
            if c in msg:
                cat = "food" if c in ("dinner", "lunch", "groceries") else c
                break
        return ("check_affordability", {"amount": amount, "category": cat})
    if re.search(r"\bshould i\s+(?:buy|spend)\b", msg, re.I):
        am = re.search(r"\$?\s*([\d,.]+)", msg)
        if am:
            return ("check_affordability", {"amount": float(am.group(1).replace(",", "")), "category": None})
    # --- Forecast ---
    if re.search(r"\b(forecast|projected|month\s*end|how much will i\s+spend)\b", msg, re.I):
        return ("get_forecast", {})
    # --- Alerts ---
    if re.search(r"\b(alerts?|warnings?|over\s+limit|near\s+limit)\b", msg, re.I):
        return ("get_alerts", {})
    # --- Seed sample data ---
    if re.search(r"\b(sample\s+data|seed\s+data|load\s+demo|add\s+sample|demo\s+data)\b", msg, re.I):
        return ("seed_data", {})
    # --- Clear data (require "confirm" for safety) ---
    if re.search(r"\bclear\s+(all\s+)?data\s+confirm\b", msg, re.I) or re.search(r"\bdelete\s+everything\s+confirm\b", msg, re.I):
        return ("clear_data", {})
    if re.search(r"\bclear\s+(all\s+)?data\b", msg, re.I) and "confirm" not in msg:
        return ("clear_data_ask_confirm", {})
    # --- Gmail sync ---
    if re.search(r"\b(sync\s+gmail|fetch\s+gmail|gmail\s+sync)\b", msg, re.I):
        return ("gmail_sync", {})
    # --- Gmail status ---
    if re.search(r"\bgmail\s+status\b", msg, re.I):
        return ("gmail_status", {})
    return None


def execute_action(intent: str, params: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Run the action and return { "message": str, "data": optional }.
    All calls use user_id for scoping.
    """
    uid = user_id or ""
    try:
        if intent == "general":
            return {
                "message": "Hi! I'm **SelavAI**, your financial assistant. You can add expenses, ask about spending, set limits, check affordability, and more. Say **Help** to see everything I can do.",
                "data": None,
            }

        if intent == "help":
            return {
                "message": (
                    "I'm your **SelavAI** assistant. I can:\n\n"
                    "• **Add expenses** — e.g. \"$50 on groceries yesterday\" or upload PDFs/images\n"
                    "• **Answer spending questions** — \"Summary for last week\", \"Break down by category\"\n"
                    "• **Limits** — \"Set food limit to 500\", \"Show my limits\", \"Remove transport limit\"\n"
                    "• **Goals** — \"My goals\", \"Add goal save 5000 by 2026\"\n"
                    "• **Affordability** — \"Can I afford 100 for dinner?\"\n"
                    "• **Forecast & alerts** — \"Forecast\", \"Alerts\", \"Projected spending\"\n"
                    "• **Data** — \"Add sample data\" (expenses, limits, goals, Wealth Hub), \"Sync Gmail\"\n"
                    "• **Clear data** — Say \"clear all data confirm\" to reset (irreversible)\n\n"
                    "Ask in plain language; I'll do it or tell you what I need."
                ),
                "data": None,
            }

        if intent == "set_limit":
            import database
            cat = (params.get("category") or "other").strip().lower()
            if cat not in LIMIT_CATEGORIES:
                cat = "other"
            amount = float(params.get("amount", 0))
            if amount <= 0:
                return {"message": "Amount must be positive.", "data": None}
            database.set_limit(cat, amount, "USD", user_id=uid)
            return {"message": f"**Limit set:** {cat} → **${amount:,.2f}** per month. Check the Budget tab.", "data": {"category": cat, "amount": amount}}

        if intent == "delete_limit":
            import database
            cat = (params.get("category") or "").strip().lower()
            if database.delete_limit(cat, user_id=uid):
                return {"message": f"Removed limit for **{cat}**.", "data": None}
            return {"message": f"No limit found for **{cat}**. Say \"Show my limits\" to see current limits.", "data": None}

        if intent == "list_limits":
            import database
            limits = database.get_limits(user_id=uid)
            if not limits:
                return {"message": "You have no limits set. Say e.g. \"Set food limit to 500\" to add one.", "data": []}
            lines = [f"• **{l['category']}**: ${float(l['amount']):,.2f}" for l in limits]
            return {"message": "**Your limits:**\n" + "\n".join(lines), "data": limits}

        if intent == "list_goals":
            import goal_service as gs
            goals = gs.get_goals(status="active")
            if not goals:
                return {"message": "You have no active goals. Say \"Add goal save 5000 by 2026\" to create one.", "data": []}
            lines = []
            for g in goals[:10]:
                t = g.get("goal_type", "")
                target = float(g.get("target_amount", 0))
                current = float(g.get("current_amount", 0))
                lines.append(f"• **{t}**: ${current:,.2f} / ${target:,.2f}")
            return {"message": "**Your goals:**\n" + "\n".join(lines), "data": goals}

        if intent == "create_goal":
            import database
            target = float(params.get("target_amount", 1000))
            current = float(params.get("current_amount", 0))
            target_date = params.get("target_date")
            gtype = (params.get("goal_type") or "savings_target").strip().lower()
            gid = database.create_goal(
                goal_type=gtype,
                target_amount=target,
                current_amount=current,
                target_date=target_date,
                category=None,
                description="",
                status="active",
                user_id=uid,
            )
            return {"message": f"**Goal created:** save **${target:,.2f}**" + (f" by {target_date}" if target_date else "") + f". (ID {gid}). See the Goals tab.", "data": {"id": gid}}

        if intent == "check_affordability":
            import affordability_service as aff
            amount = float(params.get("amount", 0))
            category = params.get("category")
            result = aff.check_affordability(amount=amount, category=category, merchant=None)
            can_afford = result.get("can_afford", False)
            rec = result.get("recommendation_text", "")
            reasons = result.get("reasons", [])
            msg = f"For **${amount:,.2f}**" + (f" ({category})" if category else "") + ": "
            msg += "**Yes, you can afford it.**" if can_afford else "**Better to skip or reduce.**"
            if rec:
                msg += f"\n{rec}"
            if reasons:
                msg += "\n" + "\n".join(f"• {r}" for r in reasons[:3])
            return {"message": msg, "data": result}

        if intent == "get_forecast":
            import forecast_service as fs
            now = datetime.now()
            proj = fs.projected_month_end(now.year, now.month)
            total = proj.get("projected_total", 0)
            by_cat = proj.get("by_category") or {}
            msg = f"**Projected spending by month end:** **${total:,.2f}** total."
            if by_cat:
                msg += "\nBy category: " + ", ".join(f"{k} ${v:,.0f}" for k, v in list(by_cat.items())[:5])
            return {"message": msg, "data": proj}

        if intent == "get_alerts":
            import database
            now = datetime.now()
            limits = database.get_limits(user_id=uid)
            spending = database.get_spending_by_category_for_month(now.year, now.month, user_id=uid)
            alerts = []
            for lim in limits:
                cat = lim["category"]
                cap = float(lim["amount"])
                spent = spending.get(cat, 0) or 0
                if cap <= 0:
                    continue
                pct = (spent / cap) * 100
                if pct >= 100:
                    alerts.append(f"**{cat}**: over limit (${spent:,.0f} / ${cap:,.0f})")
                elif pct >= 80:
                    alerts.append(f"**{cat}**: near limit ({pct:.0f}% used)")
            try:
                import forecast_service as fs
                pred = fs.predictive_alerts(now.year, now.month)
                for a in pred.get("alerts", [])[:5]:
                    alerts.append(a.get("message", str(a)))
            except Exception:
                pass
            if not alerts:
                return {"message": "No alerts right now. You're on track.", "data": []}
            return {"message": "**Alerts:**\n" + "\n".join("• " + a for a in alerts), "data": alerts}

        if intent == "seed_data":
            import seed_data
            result = seed_data.load_sample_data(user_id=uid)
            msg = f"**Sample data added:** {result.get('expenses', 0)} expenses, {result.get('limits', 0)} limits, {result.get('goals', 0)} goals."
            if result.get("salary_records") or result.get("investments") or result.get("watchlist") or result.get("liabilities"):
                parts = []
                if result.get("salary_records"): parts.append(f"{result['salary_records']} salary")
                if result.get("investments"): parts.append(f"{result['investments']} investments")
                if result.get("watchlist"): parts.append(f"{result['watchlist']} watchlist")
                if result.get("liabilities"): parts.append(f"{result['liabilities']} liabilities")
                msg += f" Wealth Hub: {', '.join(parts)}."
            msg += " Check Expenses, Budget, and Wealth Hub."
            return {"message": msg, "data": result}

        if intent == "clear_data_ask_confirm":
            return {"message": "To **clear all your data** (expenses, limits, goals, and Wealth Hub), say: **clear all data confirm**. This cannot be undone.", "data": None}

        if intent == "clear_data":
            import database
            counts = database.clear_all_data(user_id=uid)
            msg = f"**All data cleared.** Deleted: {counts.get('expenses', 0)} expenses, {counts.get('limits', 0)} limits, {counts.get('goals', 0)} goals."
            wealth = []
            if counts.get("salary_income"): wealth.append(f"{counts['salary_income']} salary")
            if counts.get("investment_transactions"): wealth.append(f"{counts['investment_transactions']} investments")
            if counts.get("stock_watchlist"): wealth.append(f"{counts['stock_watchlist']} watchlist")
            if counts.get("wealth_liabilities"): wealth.append(f"{counts['wealth_liabilities']} liabilities")
            if wealth:
                msg += f" Wealth Hub: {', '.join(wealth)}."
            return {"message": msg, "data": counts}

        if intent == "gmail_status":
            try:
                import gmail_service as gs
                import os
                connected = os.path.exists(gs.CREDENTIALS_PATH) and os.path.exists(gs.TOKEN_PATH)
                if connected:
                    return {"message": "**Gmail:** Connected. Say \"Sync Gmail\" to fetch new emails and extract expenses.", "data": {}}
                return {"message": "**Gmail:** Not connected. Add credentials and run one-time auth (see Settings → Gmail).", "data": {}}
            except Exception as e:
                return {"message": f"Gmail status error: {e}", "data": None}

        if intent == "gmail_sync":
            try:
                import gmail_service as gs
                default_query = "newer_than:7d (from:paypal.com OR from:amazon.com OR subject:receipt OR subject:payment OR subject:order)"
                added, errors = gs.sync_gmail(query=default_query, max_results=30)
                if errors:
                    return {"message": f"**Gmail sync:** Added **{added}** expense(s). Some errors occurred.", "data": {"added": added, "errors": errors}}
                return {"message": f"**Gmail sync:** Added **{added}** expense(s) from your inbox.", "data": {"added": added}}
            except Exception as e:
                return {"message": f"Gmail sync failed: {e}. Check Settings → Gmail.", "data": None}

    except Exception as e:
        return {"message": f"Action failed: {str(e)}", "data": None}
    return {"message": "I didn't understand that action.", "data": None}


def try_action(message: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    If message is an action request, execute it and return { "message", "data" }.
    Otherwise return None (caller should handle as expense or question).
    """
    parsed = parse_action(message)
    if not parsed:
        return None
    intent, params = parsed
    result = execute_action(intent, params, user_id)
    return result
