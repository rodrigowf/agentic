# researcher_tools.py

import logging
import requests
import arxiv # type: ignore
import inspect
import os
import wikipedia # Added for Wikipedia search
import time
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS # type: ignore
from pydantic import BaseModel, Field
from typing import Dict, Any, Callable, List, Optional, Type, Sequence
from autogen_core.tools import FunctionTool

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Tool 1: ArXiv Search ---

class ArxivSearchInput(BaseModel):
    """Input model for the ArXiv search tool."""
    query: str = Field(description="The search query string (e.g., 'quantum computing', 'author:John Doe'). Supports ArXiv query format.")
    max_results: int = Field(default=5, ge=1, le=50, description="Maximum number of search results to return.")

def arxiv_search(query: str, max_results: int = 5) -> str:
    """
    Searches the ArXiv repository for research papers matching the query.

    Args:
        query: The search query string. Supports ArXiv query format (e.g., 'au:Del_Maestro AND ti:checkerboard').
        max_results: The maximum number of results to return (default 5, max 50).

    Returns:
        A formatted string containing the search results (title, authors, published date, summary, URL),
        or an error message if the search fails or no results are found.
    """
    if not 1 <= max_results <= 50:
        return "Error: max_results must be between 1 and 50."
    try:
        logger.info(f"Performing ArXiv search for query: '{query}', max_results={max_results}")
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        results = list(search.results()) # Convert generator to list

        if not results:
            logger.warning(f"ArXiv search for '{query}' yielded no results.")
            return f"No results found on ArXiv for the query: '{query}'"

        output_lines = [f"ArXiv Search Results for '{query}' (Top {len(results)}):"]
        for i, result in enumerate(results):
            # Truncate long summaries to avoid excessive output
            summary = result.summary.replace("\n", " ")
            max_summary_len = 350
            truncated_summary = summary[:max_summary_len] + "..." if len(summary) > max_summary_len else summary

            output_lines.append(
                f"{i+1}. Title: {result.title}\n"
                f"   Authors: {', '.join(str(a) for a in result.authors)}\n"
                f"   Published: {result.published.strftime('%Y-%m-%d')}\n"
                f"   Summary: {truncated_summary}\n"
                f"   ArXiv URL: {result.entry_id}\n"
                f"   PDF URL: {result.pdf_url}"
            )
        logger.info(f"Successfully retrieved {len(results)} results from ArXiv for query '{query}'.")
        return "\n---\n".join(output_lines) # Separate entries clearly

    except Exception as e:
        logger.error(f"Error during ArXiv search for '{query}': {e}", exc_info=True)
        return f"An error occurred during the ArXiv search for '{query}': {str(e)}. Please check the query format or try again later."

# Create FunctionTool instance for arxiv_search
arxiv_search_tool = FunctionTool(
    func=arxiv_search,
    description="Searches the ArXiv repository (arxiv.org) for research papers based on a query string. Useful for finding academic papers (pre-prints and published) on specific topics or by specific authors in fields like physics, mathematics, computer science, quantitative biology, quantitative finance, statistics, electrical engineering, systems science, and economics.",
)

# --- Tool 2: Fetch Web Content ---

class FetchWebInput(BaseModel):
    """Input model for the fetch web content tool."""
    url: str = Field(description="The URL of the webpage to fetch and parse content from.")

def fetch_web_content(url: str) -> str:
    """
    Fetches and extracts the main textual content from a given web URL using requests and BeautifulSoup.
    It attempts to remove common clutter like navigation, headers, footers, scripts, and styles.

    Args:
        url: The URL of the webpage.

    Returns:
        The extracted text content of the page (limited in length), or a descriptive error message
        if fetching, parsing, or extraction fails.
    """
    try:
        logger.info(f"Attempting to fetch content from URL: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        response = requests.get(url, headers=headers, timeout=20) # Increased timeout
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'html' not in content_type:
            logger.warning(f"Content type for {url} is not HTML ({content_type}). Skipping parsing.")
            # Return raw text for non-HTML or handle specific types like plain text
            if 'text/plain' in content_type:
                 return response.text[:8000] + ('...' if len(response.text) > 8000 else '')
            return f"Error: Content type is not HTML ({content_type}). Cannot parse for main content."


        # Use BeautifulSoup to parse HTML and extract text
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove common clutter elements (scripts, styles, nav, header, footer)
        for element_type in ["script", "style", "nav", "header", "footer", "aside", "form", "button", "iframe"]:
             for element in soup.find_all(element_type):
                element.decompose()

        # Attempt to find the main content area (common tags/attributes)
        # This is heuristic and might need refinement for specific sites
        main_content = soup.find('main') or \
                       soup.find('article') or \
                       soup.find('div', role='main') or \
                       soup.find('div', id='content') or \
                       soup.find('div', class_='content') or \
                       soup.find('div', class_='main-content') or \
                       soup # Fallback to the whole body if no specific main area is found

        if main_content:
            # Get text, strip leading/trailing whitespace from each string, join with spaces
            text = ' '.join(t.strip() for t in main_content.stripped_strings)
        else:
             text = ' '.join(t.strip() for t in soup.stripped_strings) # Fallback extraction

        if not text:
            logger.warning(f"No significant text content could be extracted from the main area of URL: {url}")
            return f"Warning: No significant text content could be extracted from {url} after cleaning common elements."

        # Limit output length to avoid overwhelming the context window
        max_len = 8000
        truncated_text = text[:max_len] + ('...' if len(text) > max_len else '')
        logger.info(f"Successfully fetched and extracted text from {url}. Length: {len(truncated_text)} chars (truncated from {len(text)}).")
        return truncated_text

    except requests.exceptions.Timeout:
        logger.error(f"Timeout error fetching URL {url}", exc_info=False)
        return f"Error: Request timed out while trying to fetch {url}."
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP/Network Error fetching URL {url}: {e}", exc_info=True)
        return f"Error fetching URL {url}: {str(e)}. Please check the URL and network connection."
    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}", exc_info=True)
        return f"An unexpected error occurred while processing the URL {url}: {str(e)}."

# Create FunctionTool instance for fetch_web_content
fetch_web_content_tool = FunctionTool(
    func=fetch_web_content,
    description="Fetches and extracts the main textual content from a given web URL (e.g., news article, blog post, documentation). It attempts to remove clutter like navigation and ads. Returns the extracted text (up to a certain length) or an error message.",
)

# --- Tool 3: Web Search (DuckDuckGo) ---

class WebSearchInput(BaseModel):
    """Input model for the web search tool."""
    query: str = Field(description="The search query string.")
    max_results: int = Field(default=5, ge=1, le=25, description="Maximum number of search results to return.")


def web_search(query: str, max_results: int = 5) -> str:
    """
    Performs a web search preferring Google Programmable Search (CSE) for high-demand reliability,
    with automatic fallback to DuckDuckGo when Google credentials are not configured.

    Environment variables for Google CSE:
      - GOOGLE_CSE_API_KEY: Google API key
      - GOOGLE_CSE_CX: Programmable Search Engine ID
      - Optional: GOOGLE_CSE_SAFE (off|medium|high), GOOGLE_CSE_GL (country code), GOOGLE_CSE_LR (e.g. lang_en)

    Args:
        query: The search query.
        max_results: The maximum number of results to return (default 5, max 25).

    Returns:
        A formatted string containing the search results (title, snippet, URL),
        or an error message if the search fails or no results are found.
    """
    if not 1 <= max_results <= 25:
        return "Error: max_results must be between 1 and 25."
    try:
        api_key = os.getenv("GOOGLE_CSE_API_KEY")
        cx = os.getenv("GOOGLE_CSE_CX")

        if api_key and cx:
            logger.info(
                f"Using Google Programmable Search (CSE) for query: '{query}', max_results={max_results}"
            )
            results: List[Dict[str, str]] = []
            session = requests.Session()
            base_url = "https://www.googleapis.com/customsearch/v1"
            safe = os.getenv("GOOGLE_CSE_SAFE", "off")
            gl = os.getenv("GOOGLE_CSE_GL")  # e.g., 'us', 'br'
            lr = os.getenv("GOOGLE_CSE_LR")  # e.g., 'lang_en'

            # Google CSE returns up to 10 results per request; paginate if needed
            start = 1
            remaining = max_results
            while remaining > 0 and start <= 91 and len(results) < max_results:
                num = min(10, remaining)
                params = {
                    "key": api_key,
                    "cx": cx,
                    "q": query,
                    "num": num,
                    "start": start,
                    "safe": safe,
                }
                if gl:
                    params["gl"] = gl
                if lr:
                    params["lr"] = lr

                # Retry with simple exponential backoff for transient errors/rate limits
                last_exc: Optional[Exception] = None
                for attempt in range(3):
                    try:
                        resp = session.get(base_url, params=params, timeout=15)
                        # Handle common throttling explicitly
                        if resp.status_code in (429, 500, 502, 503, 504):
                            raise requests.RequestException(
                                f"Transient HTTP {resp.status_code}: {resp.text[:200]}"
                            )
                        resp.raise_for_status()
                        data = resp.json()
                        items = data.get("items", []) or []
                        for it in items:
                            results.append(
                                {
                                    "title": it.get("title") or "N/A",
                                    "body": it.get("snippet") or "N/A",
                                    "href": it.get("link") or "N/A",
                                }
                            )
                        # Update counters
                        if not items:
                            remaining = 0
                        else:
                            remaining = max_results - len(results)
                            start += len(items)
                        break  # success
                    except (requests.Timeout, requests.RequestException) as e:
                        last_exc = e
                        # Backoff: 0.8s, 1.6s, 3.2s
                        time.sleep(0.8 * (2 ** attempt))
                else:
                    # Retries exhausted
                    logger.warning(
                        f"Google CSE request failed after retries for query '{query}': {last_exc}"
                    )
                    break

            results = results[:max_results]
            if not results:
                logger.warning(
                    f"Google CSE returned no results for query '{query}'. Falling back to DuckDuckGo."
                )
            else:
                output_lines = [
                    f"Web Search Results (Google CSE) for '{query}' (Found {len(results)}):"
                ]
                for i, result in enumerate(results):
                    title = result.get("title", "N/A")
                    snippet = (result.get("body", "N/A") or "").replace("\n", " ")
                    url = result.get("href", "N/A")
                    output_lines.append(
                        f"{i+1}. Title: {title}\n"
                        f"   Snippet: {snippet}\n"
                        f"   URL: {url}"
                    )
                logger.info(
                    f"Successfully retrieved {len(results)} results from Google CSE for query '{query}'."
                )
                return "\n---\n".join(output_lines)

        # Fallback to DuckDuckGo if Google CSE is not configured or returned nothing
        logger.info(
            f"Falling back to DuckDuckGo for query: '{query}', max_results={max_results}"
        )
        with DDGS() as ddgs:
            ddg_results = list(ddgs.text(query, max_results=max_results))
        if not ddg_results:
            logger.warning(f"DuckDuckGo search for '{query}' yielded no results.")
            return f"No results found for the query: '{query}'"

        output_lines = [f"Web Search Results (DuckDuckGo) for '{query}' (Found {len(ddg_results)}):"]
        for i, result in enumerate(ddg_results):
            title = result.get("title", "N/A")
            snippet = (result.get("body", "N/A") or "").replace("\n", " ")
            url = result.get("href", "N/A")
            output_lines.append(
                f"{i+1}. Title: {title}\n"
                f"   Snippet: {snippet}\n"
                f"   URL: {url}"
            )
        logger.info(
            f"Successfully retrieved {len(ddg_results)} results from DuckDuckGo for query '{query}'."
        )
        return "\n---\n".join(output_lines)

    except Exception as e:
        logger.error(f"Error during web search for '{query}': {e}", exc_info=True)
        return (
            f"An error occurred during the web search for '{query}': {str(e)}."
            " Please try again later."
        )

# Create FunctionTool instance for web_search
web_search_tool = FunctionTool(
    func=web_search,
    description=(
        "Performs a web search using Google Programmable Search (CSE) for high-demand reliability, "
        "with automatic fallback to DuckDuckGo when Google credentials are unavailable. Returns a list "
        "of results including title, snippet, and URL. Configure GOOGLE_CSE_API_KEY and GOOGLE_CSE_CX."
    ),
)

# --- Tool 4: Wikipedia Search ---

class WikipediaSearchInput(BaseModel):
    """Input model for the Wikipedia search tool."""
    query: str = Field(description="The search query string for Wikipedia.")
    lang: str = Field(default="en", description="The language code for Wikipedia (e.g., 'en', 'es', 'fr').")
    max_results: int = Field(default=3, ge=1, le=10, description="Maximum number of page summaries to return.")

def wikipedia_search(query: str, lang: str = "en", max_results: int = 3) -> str:
    """
    Searches Wikipedia for articles matching the query and returns summaries.

    Args:
        query: The search query string.
        lang: The language code for Wikipedia (default 'en').
        max_results: The maximum number of page summaries to return (default 3, max 10).

    Returns:
        A formatted string containing the search results (title, summary, URL),
        or an error message if the search fails or no results are found.
    """
    if not 1 <= max_results <= 10:
        return "Error: max_results must be between 1 and 10."
    try:
        logger.info(f"Performing Wikipedia search for query: '{query}', lang='{lang}', max_results={max_results}")
        wikipedia.set_lang(lang)

        # Search for pages
        search_results = wikipedia.search(query, results=max_results * 2) # Get more results initially to filter disambiguation
        if not search_results:
            logger.warning(f"Wikipedia search for '{query}' (lang={lang}) yielded no initial results.")
            return f"No results found on Wikipedia ({lang}) for the query: '{query}'"

        output_lines = [f"Wikipedia Search Results for '{query}' (Lang: {lang}, Top {max_results}):"]
        count = 0
        processed_titles = set() # Avoid duplicates if search returns similar titles

        for title in search_results:
            if count >= max_results:
                break
            if title in processed_titles:
                continue

            try:
                # Attempt to get the page summary
                page = wikipedia.page(title=title, auto_suggest=False, redirect=True) # Follow redirects
                processed_titles.add(page.title) # Add the actual page title after potential redirect

                # Limit summary length
                max_summary_len = 500
                summary = page.summary.replace("\n", " ")
                truncated_summary = summary[:max_summary_len] + "..." if len(summary) > max_summary_len else summary

                output_lines.append(
                    f"{count+1}. Title: {page.title}\n"
                    f"   Summary: {truncated_summary}\n"
                    f"   URL: {page.url}"
                )
                count += 1
            except wikipedia.exceptions.PageError:
                logger.warning(f"Wikipedia page '{title}' not found or is a disambiguation page (query: '{query}', lang={lang}). Skipping.")
                processed_titles.add(title) # Add original title to avoid re-processing
            except wikipedia.exceptions.DisambiguationError as e:
                logger.warning(f"Wikipedia disambiguation error for '{title}' (query: '{query}', lang={lang}): {e.options[:3]}... Skipping.")
                processed_titles.add(title) # Add original title to avoid re-processing
            except Exception as page_e: # Catch other potential errors during page fetching/processing
                 logger.error(f"Error processing Wikipedia page '{title}' for query '{query}' (lang={lang}): {page_e}", exc_info=False)
                 processed_titles.add(title) # Add original title to avoid re-processing

        if count == 0:
             logger.warning(f"Wikipedia search for '{query}' (lang={lang}) found potential pages, but none could be summarized (e.g., all disambiguation).")
             return f"Found potential matches for '{query}' on Wikipedia ({lang}), but could not retrieve valid page summaries (they might be disambiguation pages)."


        logger.info(f"Successfully retrieved {count} summaries from Wikipedia for query '{query}' (lang={lang}).")
        return "\n---\n".join(output_lines) # Separate entries clearly

    except wikipedia.exceptions.WikipediaException as e:
        logger.error(f"Wikipedia API error during search for '{query}' (lang={lang}): {e}", exc_info=True)
        return f"A Wikipedia specific error occurred during the search for '{query}' (lang={lang}): {str(e)}. Please check the language code or try again later."
    except Exception as e:
        logger.error(f"Error during Wikipedia search for '{query}' (lang={lang}): {e}", exc_info=True)
        return f"An unexpected error occurred during the Wikipedia search for '{query}' (lang={lang}): {str(e)}. Please try again later."

# Create FunctionTool instance for wikipedia_search
wikipedia_search_tool = FunctionTool(
    func=wikipedia_search,
    description="Searches Wikipedia in a specified language for articles matching a query. Returns a list of page summaries including title, summary snippet, and URL. Useful for getting encyclopedic information.",
)

# --- Helper function to get all FunctionTools from this module ---
def get_tools_from_this_module() -> List[FunctionTool]:
    """
    Inspects the current module and returns a list of all FunctionTool instances defined within it.
    """
    tools = []
    current_module = inspect.getmodule(inspect.currentframe())
    if current_module:
        for name, obj in inspect.getmembers(current_module):
            if isinstance(obj, FunctionTool):
                tools.append(obj)
    return tools

# --- Main execution block for testing purposes ---
if __name__ == "__main__":
    print("--- Discovering Tools Defined in this File ---")
    discovered_tools = get_tools_from_this_module()
    for tool in discovered_tools:
        print(f"\nTool: {tool.name}")
        print(f"  Description: {tool.description}")
        print(f"  Function Assigned: {callable(tool._function)}")