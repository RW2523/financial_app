"""
Fetch finance-related news via Tavily Search API.
Set TAVILY_API_KEY in env (or .env) to enable. Topic 'finance' returns money, stocks, exchange, etc.
"""
from typing import List, Dict, Any

from config import TAVILY_API_KEY


# Broad query so we get money, exchange, stocks, markets, economy
DEFAULT_FINANCE_QUERY = (
    "finance news: money exchange rates stock market prices economy "
    "central banks interest rates inflation currency"
)


def fetch_finance_news(
    query: str = None,
    max_results: int = 15,
    search_depth: str = "basic",
    time_range: str = "week",
) -> Dict[str, Any]:
    """
    Call Tavily Search with topic=finance. Returns normalized list of articles.
    If TAVILY_API_KEY is missing, returns {"results": [], "error": "TAVILY_API_KEY not set"}.
    """
    if not TAVILY_API_KEY:
        return {
            "results": [],
            "query": query or DEFAULT_FINANCE_QUERY,
            "error": "TAVILY_API_KEY not set. Add it to .env or environment to enable finance news.",
        }

    try:
        from tavily import TavilyClient
    except ImportError:
        return {
            "results": [],
            "query": query or DEFAULT_FINANCE_QUERY,
            "error": "tavily-python not installed. Run: pip install tavily-python",
        }

    q = (query or DEFAULT_FINANCE_QUERY).strip() or DEFAULT_FINANCE_QUERY
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(
            query=q,
            topic="finance",
            search_depth=search_depth,
            max_results=max(min(max_results, 20), 1),
            time_range=time_range,
        )
    except Exception as e:
        return {
            "results": [],
            "query": q,
            "error": str(e),
        }

    raw_results = response.get("results") or []
    results: List[Dict[str, Any]] = []
    for r in raw_results:
        content = (r.get("content") or "").strip()
        title = r.get("title") or (content.split("\n")[0][:80] if content else "") or r.get("url", "")
        results.append({
            "title": title,
            "url": r.get("url", ""),
            "content": content[:500],
            "score": r.get("score"),
        })

    return {
        "results": results,
        "query": response.get("query", q),
        "response_time": response.get("response_time"),
    }
