# mcp_server_3.py – Web search MCP server

"""Provides two tools for the Multi‑Agent System:

* ``web_search`` – uses the Tavily API to perform a web search and returns a
  dictionary containing the raw ``results`` list and a human‑readable ``formatted``
  string.
* ``download_raw_html_from_url`` – fetches a URL and returns the cleaned text
  content.

The implementation is deliberately lightweight and avoids any duplicate
definitions or stray emojis that caused UnicodeEncodeError on Windows.
"""

from mcp.server.fastmcp import FastMCP, Context
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import sys
import traceback
import asyncio
from datetime import datetime, timedelta
import re
from tavily import TavilyClient
import os
from dotenv import load_dotenv
from pathlib import Path

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# ---------------------------------------------------------------------------
# Helper classes
# ---------------------------------------------------------------------------
class RateLimiter:
    """Simple rate limiter – max *requests_per_minute* calls per minute."""

    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.requests: List[datetime] = []

    async def acquire(self) -> None:
        now = datetime.now()
        # Keep only timestamps within the last minute
        self.requests = [req for req in self.requests if now - req < timedelta(minutes=1)]
        if len(self.requests) >= self.requests_per_minute:
            wait = 60 - (now - self.requests[0]).total_seconds()
            if wait > 0:
                await asyncio.sleep(wait)
        self.requests.append(now)


class TavilySearcher:
    """Thin wrapper around ``tavily`` with deterministic logging."""

    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            sys.stderr.write(
                "WARNING: TAVILY_API_KEY not found in .env file. Web search will fail.\n"
            )
            sys.stderr.flush()
        self.client = TavilyClient(api_key=api_key) if api_key else None

    def format_results_for_llm(self, results: List[Dict[str, Any]]) -> str:
        if not results:
            return "No results were found for your search query."
        lines = [f"Found {len(results)} search results:\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r.get('title', 'No Title')}")
            lines.append(f"   URL: {r.get('url', 'No URL')}")
            lines.append(f"   Summary: {r.get('content', 'No Summary')}")
            lines.append("")
        return "\n".join(lines)

    def search_sync(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        sys.stderr.write("\n--- TavilySearcher.search_sync ---\n")
        sys.stderr.flush()
        try:
            if not self.client:
                sys.stderr.write("[ERROR] Tavily client not initialized\n")
                sys.stderr.flush()
                return []
            sys.stderr.write("[OK] Tavily client exists\n")
            sys.stderr.write("[INFO] Calling Tavily API...\n")
            sys.stderr.flush()
            response = self.client.search(
                query=query,
                max_results=max_results,
                include_answer=False,
                include_raw_content=False,
            )
            sys.stderr.write("[OK] Tavily API responded\n")
            sys.stderr.write(f"[INFO] Response type: {type(response)}\n")
            sys.stderr.flush()
            results = response.get("results", [])
            sys.stderr.write(f"[OK] Extracted {len(results)} results\n")
            if results:
                sys.stderr.write(
                    f"[INFO] First result title: {results[0].get('title', 'N/A')[:50]}\n"
                )
            sys.stderr.write("--- End search_sync ---\n\n")
            sys.stderr.flush()
            return results
        except Exception as e:
            sys.stderr.write(
                f"[ERROR] EXCEPTION in search_sync: {type(e).__name__}: {str(e)}\n"
            )
            sys.stderr.flush()
            traceback.print_exc(file=sys.stderr)
            return []


class WebContentFetcher:
    """Fetches a URL and returns plain text (max 8000 chars)."""

    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_minute=20)

    async def fetch_and_parse(self, url: str, ctx: Context) -> str:
        try:
            await self.rate_limiter.acquire()
            await ctx.info(f"Fetching content from: {url}")
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                    follow_redirects=True,
                    timeout=30.0,
                )
                resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for el in soup(["script", "style", "nav", "header", "footer"]):
                el.decompose()
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            cleaned = " ".join(chunk for chunk in chunks if chunk)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if len(cleaned) > 8000:
                cleaned = cleaned[:8000] + "... [content truncated]"
            await ctx.info(f"Successfully fetched and parsed content ({len(cleaned)} characters)")
            return cleaned
        except httpx.TimeoutException:
            await ctx.error(f"Request timed out for URL: {url}")
            return "Error: The request timed out while trying to fetch the webpage."
        except httpx.HTTPError as e:
            await ctx.error(f"HTTP error occurred while fetching {url}: {str(e)}")
            return f"Error: Could not access the webpage ({str(e)})"
        except Exception as e:
            await ctx.error(f"Error fetching content from {url}: {str(e)}")
            return f"Error: An unexpected error occurred while fetching the webpage ({str(e)})"

# ---------------------------------------------------------------------------
# MCP server initialisation
# ---------------------------------------------------------------------------
mcp = FastMCP("web-search")
searcher = TavilySearcher()
fetcher = WebContentFetcher()

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------
@mcp.tool()
async def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web via Tavily and return ``{"results": ..., "formatted": ...}``."""
    sys.stderr.write("\n" + "=" * 60 + "\n")
    sys.stderr.write("[TOOL] web_search called with:\n")
    sys.stderr.write(f"   query: {query}\n")
    sys.stderr.write(f"   max_results: {max_results}\n")
    sys.stderr.flush()
    try:
        sys.stderr.write("[INFO] Calling searcher.search_sync...\n")
        sys.stderr.flush()
        results = await asyncio.to_thread(searcher.search_sync, query, max_results)
        sys.stderr.write(f"[OK] search_sync returned {len(results)} results\n")
        sys.stderr.flush()
        formatted = searcher.format_results_for_llm(results)
        sys.stderr.write(f"[OK] Formatted result length: {len(formatted)} chars\n")
        sys.stderr.flush()
        return {"results": results, "formatted": formatted}
    except Exception as e:
        sys.stderr.write(
            f"[ERROR] EXCEPTION in web_search: {type(e).__name__}: {str(e)}\n"
        )
        sys.stderr.flush()
        traceback.print_exc(file=sys.stderr)
        return {"error": f"An error occurred while searching: {str(e)}"}


@mcp.tool()
async def download_raw_html_from_url(url: str, ctx: Context) -> str:
    """Fetch a URL and return cleaned text content."""
    return await fetcher.fetch_and_parse(url, ctx)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.stderr.write("mcp_server_3.py starting\n")
    sys.stderr.flush()
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()
    else:
        mcp.run(transport="stdio")
        sys.stderr.write("\nShutting down...\n")
        sys.stderr.flush()
