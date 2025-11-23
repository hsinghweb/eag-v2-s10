from mcp.server.fastmcp import FastMCP, Context
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
import sys
import traceback
import asyncio
from datetime import datetime, timedelta
import re
from tavily import TavilyClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root explicitly
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class RateLimiter:
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.requests = []

    async def acquire(self):
        now = datetime.now()
        self.requests = [
            req for req in self.requests if now - req < timedelta(minutes=1)
        ]

        if len(self.requests) >= self.requests_per_minute:
            wait_time = 60 - (now - self.requests[0]).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        self.requests.append(now)


class TavilySearcher:
    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            sys.stderr.write("WARNING: TAVILY_API_KEY not found in .env file. Web search will fail.\n")
            sys.stderr.flush()
        self.client = TavilyClient(api_key=api_key) if api_key else None

    def format_results_for_llm(self, results: List[Dict[str, Any]]) -> str:
        if not results:
            return "No results were found for your search query."

        output = []
        output.append(f"Found {len(results)} search results:\n")

        for i, result in enumerate(results, 1):
            output.append(f"{i}. {result.get('title', 'No Title')}")
            output.append(f"   URL: {result.get('url', 'No URL')}")
            output.append(f"   Summary: {result.get('content', 'No Summary')}")
            output.append("")

        return "\n".join(output)

    def search_sync(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Synchronous search method"""
        try:
            if not self.client:
                sys.stderr.write("ERROR: Tavily client not initialized\n")
                sys.stderr.flush()
                return []
                
            sys.stderr.write(f"DEBUG: Searching Tavily for '{query}' with max_results={max_results}\n")
            sys.stderr.flush()
            
            # Direct synchronous call - no threading
            response = self.client.search(
                query=query,
                max_results=max_results,
                include_answer=False,
                include_raw_content=False
            )
            results = response.get('results', [])
            
            sys.stderr.write(f"DEBUG: Found {len(results)} results\n")
            sys.stderr.flush()
            return results

        except Exception as e:
            sys.stderr.write(f"DEBUG: Error in Tavily search: {e}\n")
            sys.stderr.flush()
            traceback.print_exc(file=sys.stderr)
            return []


class WebContentFetcher:
    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_minute=20)

    async def fetch_and_parse(self, url: str, ctx: Context) -> str:
        try:
            await self.rate_limiter.acquire()
            await ctx.info(f"Fetching content from: {url}")

            async with httpx.AsyncClient() as client:
                result = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    follow_redirects=True,
                    timeout=30.0,
                )
                result.raise_for_status()

            soup = BeautifulSoup(result.text, "html.parser")
            for element in soup(["script", "style", "nav", "header", "footer"]):
                element.decompose()

            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)
            text = re.sub(r"\s+", " ", text).strip()

            if len(text) > 8000:
                text = text[:8000] + "... [content truncated]"

            await ctx.info(f"Successfully fetched and parsed content ({len(text)} characters)")
            return text

        except httpx.TimeoutException:
            await ctx.error(f"Request timed out for URL: {url}")
            return "Error: The request timed out while trying to fetch the webpage."
        except httpx.HTTPError as e:
            await ctx.error(f"HTTP error occurred while fetching {url}: {str(e)}")
            return f"Error: Could not access the webpage ({str(e)})"
        except Exception as e:
            await ctx.error(f"Error fetching content from {url}: {str(e)}")
            return f"Error: An unexpected error occurred while fetching the webpage ({str(e)})"


# Initialize FastMCP server
mcp = FastMCP("web-search")
searcher = TavilySearcher()
fetcher = WebContentFetcher()


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using Tavily API."""
    try:
        results = searcher.search_sync(query, max_results)
        return searcher.format_results_for_llm(results)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return f"An error occurred while searching: {str(e)}"


@mcp.tool()
async def download_raw_html_from_url(url: str, ctx: Context) -> str:
    """Fetch webpage content."""
    return await fetcher.fetch_and_parse(url, ctx)


if __name__ == "__main__":
    sys.stderr.write("mcp_server_3.py starting\n")
    sys.stderr.flush()
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()
    else:
        mcp.run(transport="stdio")
        sys.stderr.write("\nShutting down...\n")
