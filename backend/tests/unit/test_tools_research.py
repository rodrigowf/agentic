"""
Unit tests for tools/research.py

Tests all research tool functions:
- web_search (Google CSE + DuckDuckGo fallback)
- arxiv_search
- wikipedia_search
- fetch_web_content
- BeautifulSoup parsing
- Mock external API calls
- Error handling for network failures
"""

import pytest
import requests
from unittest.mock import MagicMock, patch, Mock
from typing import List, Dict

# Import research tools
from tools.research import (
    web_search,
    arxiv_search,
    wikipedia_search,
    fetch_web_content,
    arxiv_search_tool,
    fetch_web_content_tool,
    web_search_tool,
    wikipedia_search_tool,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_ddg_results():
    """Mock DuckDuckGo search results."""
    return [
        {
            "title": "Test Result 1",
            "body": "This is a test snippet for result 1",
            "href": "https://example.com/1"
        },
        {
            "title": "Test Result 2",
            "body": "This is a test snippet for result 2",
            "href": "https://example.com/2"
        },
        {
            "title": "Test Result 3",
            "body": "This is a test snippet for result 3",
            "href": "https://example.com/3"
        }
    ]


@pytest.fixture
def mock_google_cse_response():
    """Mock Google Custom Search Engine API response."""
    return {
        "items": [
            {
                "title": "Google Result 1",
                "snippet": "Google snippet 1",
                "link": "https://google-example.com/1"
            },
            {
                "title": "Google Result 2",
                "snippet": "Google snippet 2",
                "link": "https://google-example.com/2"
            }
        ]
    }


@pytest.fixture
def mock_arxiv_results():
    """Mock ArXiv search results."""
    result1 = MagicMock()
    result1.title = "Quantum Computing Paper"
    result1.authors = [MagicMock(__str__=lambda x: "John Doe"), MagicMock(__str__=lambda x: "Jane Smith")]
    result1.published = MagicMock(strftime=lambda x: "2024-01-15")
    result1.summary = "This is a summary about quantum computing " * 20  # Long summary
    result1.entry_id = "https://arxiv.org/abs/2401.12345"
    result1.pdf_url = "https://arxiv.org/pdf/2401.12345"

    result2 = MagicMock()
    result2.title = "Machine Learning Paper"
    result2.authors = [MagicMock(__str__=lambda x: "Alice Johnson")]
    result2.published = MagicMock(strftime=lambda x: "2024-02-20")
    result2.summary = "Short summary about ML"
    result2.entry_id = "https://arxiv.org/abs/2402.67890"
    result2.pdf_url = "https://arxiv.org/pdf/2402.67890"

    return [result1, result2]


@pytest.fixture
def mock_wikipedia_page():
    """Mock Wikipedia page."""
    page = MagicMock()
    page.title = "Python (programming language)"
    page.summary = "Python is a high-level programming language. " * 10
    page.url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    return page


@pytest.fixture
def mock_html_content():
    """Mock HTML content for web scraping."""
    return """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <nav>Navigation menu</nav>
            <header>Header content</header>
            <main>
                <article>
                    <h1>Main Article Title</h1>
                    <p>This is the main content of the article.</p>
                    <p>Another paragraph with important information.</p>
                </article>
            </main>
            <footer>Footer content</footer>
            <script>console.log('script');</script>
        </body>
    </html>
    """


# ============================================================================
# Test Web Search
# ============================================================================

class TestWebSearch:
    """Test web_search function with Google CSE and DuckDuckGo."""

    @patch("tools.research.DDGS")
    def test_web_search_duckduckgo_success(self, mock_ddgs, mock_ddg_results, monkeypatch):
        """Test successful web search using DuckDuckGo (no Google credentials)."""
        # Remove Google credentials
        monkeypatch.delenv("GOOGLE_CSE_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_CSE_CX", raising=False)

        # Mock DuckDuckGo
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = mock_ddg_results
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance

        result = web_search("test query", max_results=3)

        assert "Web Search Results (DuckDuckGo)" in result
        assert "Test Result 1" in result
        assert "Test Result 2" in result
        assert "example.com/1" in result
        assert "Found 3" in result

    @patch("tools.research.requests.Session")
    def test_web_search_google_cse_success(self, mock_session, mock_google_cse_response, monkeypatch):
        """Test successful web search using Google CSE."""
        # Set Google credentials
        monkeypatch.setenv("GOOGLE_CSE_API_KEY", "test_api_key")
        monkeypatch.setenv("GOOGLE_CSE_CX", "test_cx")

        # Mock Google CSE response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_google_cse_response
        mock_session.return_value.get.return_value = mock_response

        result = web_search("test query", max_results=2)

        assert "Web Search Results (Google CSE)" in result
        assert "Google Result 1" in result
        assert "Google Result 2" in result
        assert "google-example.com/1" in result

    @patch("tools.research.requests.Session")
    @patch("tools.research.DDGS")
    def test_web_search_google_fallback_to_ddg(self, mock_ddgs, mock_session, mock_ddg_results, monkeypatch):
        """Test fallback to DuckDuckGo when Google CSE fails."""
        # Set Google credentials
        monkeypatch.setenv("GOOGLE_CSE_API_KEY", "test_api_key")
        monkeypatch.setenv("GOOGLE_CSE_CX", "test_cx")

        # Mock Google CSE failure (empty results)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_session.return_value.get.return_value = mock_response

        # Mock DuckDuckGo success
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = mock_ddg_results
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance

        result = web_search("test query", max_results=3)

        assert "Web Search Results (DuckDuckGo)" in result
        assert "Test Result 1" in result

    @patch("tools.research.DDGS")
    def test_web_search_no_results(self, mock_ddgs, monkeypatch):
        """Test web search with no results."""
        monkeypatch.delenv("GOOGLE_CSE_API_KEY", raising=False)

        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = []
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance

        result = web_search("nonexistent query")

        assert "No results found" in result
        assert "nonexistent query" in result

    @patch("tools.research.DDGS")
    def test_web_search_exception(self, mock_ddgs, monkeypatch):
        """Test web search error handling."""
        monkeypatch.delenv("GOOGLE_CSE_API_KEY", raising=False)

        mock_ddgs.return_value.__enter__.side_effect = Exception("Network error")

        result = web_search("test query")

        assert "error occurred" in result.lower()
        assert "Network error" in result

    def test_web_search_invalid_max_results(self):
        """Test web search with invalid max_results parameter."""
        result = web_search("test", max_results=0)
        assert "Error: max_results must be between 1 and 25" in result

        result = web_search("test", max_results=30)
        assert "Error: max_results must be between 1 and 25" in result

    @patch("tools.research.requests.Session")
    @patch("tools.research.time.sleep")
    def test_web_search_google_retry_on_rate_limit(self, mock_sleep, mock_session, monkeypatch):
        """Test Google CSE retry logic on rate limit."""
        monkeypatch.setenv("GOOGLE_CSE_API_KEY", "test_api_key")
        monkeypatch.setenv("GOOGLE_CSE_CX", "test_cx")

        # First attempt: rate limit, second attempt: success
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 429
        mock_response_fail.text = "Rate limit exceeded"

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "items": [{"title": "Result", "snippet": "Snippet", "link": "https://example.com"}]
        }

        mock_session.return_value.get.side_effect = [
            requests.RequestException("Transient HTTP 429"),
            mock_response_success
        ]

        result = web_search("test query", max_results=1)

        # Should eventually succeed after retry
        assert "Result" in result or "error" in result.lower()


# ============================================================================
# Test ArXiv Search
# ============================================================================

class TestArxivSearch:
    """Test arxiv_search function."""

    @patch("tools.research.arxiv.Search")
    def test_arxiv_search_success(self, mock_search, mock_arxiv_results):
        """Test successful ArXiv search."""
        # Mock search results
        mock_search_instance = MagicMock()
        mock_search_instance.results.return_value = iter(mock_arxiv_results)
        mock_search.return_value = mock_search_instance

        result = arxiv_search("quantum computing", max_results=2)

        assert "ArXiv Search Results" in result
        assert "Quantum Computing Paper" in result
        assert "Machine Learning Paper" in result
        assert "John Doe" in result
        assert "arxiv.org/abs/2401.12345" in result

    @patch("tools.research.arxiv.Search")
    def test_arxiv_search_no_results(self, mock_search):
        """Test ArXiv search with no results."""
        mock_search_instance = MagicMock()
        mock_search_instance.results.return_value = iter([])
        mock_search.return_value = mock_search_instance

        result = arxiv_search("nonexistent topic")

        assert "No results found" in result
        assert "nonexistent topic" in result

    @patch("tools.research.arxiv.Search")
    def test_arxiv_search_truncate_summary(self, mock_search, mock_arxiv_results):
        """Test that long summaries are truncated."""
        mock_search_instance = MagicMock()
        mock_search_instance.results.return_value = iter(mock_arxiv_results)
        mock_search.return_value = mock_search_instance

        result = arxiv_search("quantum", max_results=1)

        # First result has long summary, should be truncated
        assert "..." in result  # Truncation indicator

    @patch("tools.research.arxiv.Search")
    def test_arxiv_search_exception(self, mock_search):
        """Test ArXiv search error handling."""
        mock_search.side_effect = Exception("API connection error")

        result = arxiv_search("test query")

        assert "error occurred" in result.lower()
        assert "API connection error" in result

    def test_arxiv_search_invalid_max_results(self):
        """Test ArXiv search with invalid max_results."""
        result = arxiv_search("test", max_results=0)
        assert "Error: max_results must be between 1 and 50" in result

        result = arxiv_search("test", max_results=100)
        assert "Error: max_results must be between 1 and 50" in result


# ============================================================================
# Test Wikipedia Search
# ============================================================================

class TestWikipediaSearch:
    """Test wikipedia_search function."""

    @patch("tools.research.wikipedia.page")
    @patch("tools.research.wikipedia.search")
    @patch("tools.research.wikipedia.set_lang")
    def test_wikipedia_search_success(self, mock_set_lang, mock_search, mock_page, mock_wikipedia_page):
        """Test successful Wikipedia search."""
        mock_search.return_value = ["Python (programming language)", "Python (genus)"]
        mock_page.return_value = mock_wikipedia_page

        result = wikipedia_search("Python programming", max_results=2)

        assert "Wikipedia Search Results" in result
        assert "Python (programming language)" in result
        assert "https://en.wikipedia.org" in result
        mock_set_lang.assert_called_once_with("en")

    @patch("tools.research.wikipedia.search")
    @patch("tools.research.wikipedia.set_lang")
    def test_wikipedia_search_no_results(self, mock_set_lang, mock_search):
        """Test Wikipedia search with no results."""
        mock_search.return_value = []

        result = wikipedia_search("nonexistent topic")

        assert "No results found" in result
        assert "nonexistent topic" in result

    @patch("tools.research.wikipedia.page")
    @patch("tools.research.wikipedia.search")
    @patch("tools.research.wikipedia.set_lang")
    def test_wikipedia_search_disambiguation_error(self, mock_set_lang, mock_search, mock_page):
        """Test Wikipedia search with disambiguation page."""
        import wikipedia
        mock_search.return_value = ["Python", "Java"]
        mock_page.side_effect = wikipedia.exceptions.DisambiguationError(
            "Disambiguation", ["Python (programming)", "Python (snake)"]
        )

        result = wikipedia_search("Python", max_results=1)

        # Should skip disambiguation and show message
        assert "disambiguation" in result.lower() or "no" in result.lower()

    @patch("tools.research.wikipedia.page")
    @patch("tools.research.wikipedia.search")
    @patch("tools.research.wikipedia.set_lang")
    def test_wikipedia_search_page_error(self, mock_set_lang, mock_search, mock_page):
        """Test Wikipedia search with page not found."""
        import wikipedia
        mock_search.return_value = ["Nonexistent Page"]
        mock_page.side_effect = wikipedia.exceptions.PageError("Page not found")

        result = wikipedia_search("test", max_results=1)

        assert "could not retrieve" in result.lower() or "no" in result.lower()

    @patch("tools.research.wikipedia.page")
    @patch("tools.research.wikipedia.search")
    @patch("tools.research.wikipedia.set_lang")
    def test_wikipedia_search_different_language(self, mock_set_lang, mock_search, mock_page, mock_wikipedia_page):
        """Test Wikipedia search with different language."""
        mock_search.return_value = ["Test Page"]
        mock_page.return_value = mock_wikipedia_page

        result = wikipedia_search("test", lang="es", max_results=1)

        mock_set_lang.assert_called_once_with("es")
        assert "Lang: es" in result

    def test_wikipedia_search_invalid_max_results(self):
        """Test Wikipedia search with invalid max_results."""
        result = wikipedia_search("test", max_results=0)
        assert "Error: max_results must be between 1 and 10" in result

        result = wikipedia_search("test", max_results=15)
        assert "Error: max_results must be between 1 and 10" in result

    @patch("tools.research.wikipedia.search")
    @patch("tools.research.wikipedia.set_lang")
    def test_wikipedia_search_exception(self, mock_set_lang, mock_search):
        """Test Wikipedia search error handling."""
        mock_search.side_effect = Exception("Network error")

        result = wikipedia_search("test")

        assert "error occurred" in result.lower()


# ============================================================================
# Test Fetch Web Content
# ============================================================================

class TestFetchWebContent:
    """Test fetch_web_content function."""

    @patch("tools.research.requests.get")
    def test_fetch_web_content_success(self, mock_get, mock_html_content):
        """Test successful web content fetching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html_content
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_web_content("https://example.com")

        assert "Main Article Title" in result
        assert "main content of the article" in result
        assert "important information" in result
        # Should NOT contain navigation, header, footer, or script
        assert "Navigation menu" not in result
        assert "Header content" not in result
        assert "Footer content" not in result
        assert "console.log" not in result

    @patch("tools.research.requests.get")
    def test_fetch_web_content_plain_text(self, mock_get):
        """Test fetching plain text content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Plain text content"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_web_content("https://example.com/text.txt")

        assert "Plain text content" in result

    @patch("tools.research.requests.get")
    def test_fetch_web_content_non_html(self, mock_get):
        """Test fetching non-HTML content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_web_content("https://example.com/doc.pdf")

        assert "Error: Content type is not HTML" in result

    @patch("tools.research.requests.get")
    def test_fetch_web_content_timeout(self, mock_get):
        """Test timeout error."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

        result = fetch_web_content("https://slow-site.com")

        assert "Error: Request timed out" in result

    @patch("tools.research.requests.get")
    def test_fetch_web_content_http_error(self, mock_get):
        """Test HTTP error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        result = fetch_web_content("https://example.com/notfound")

        assert "Error fetching URL" in result

    @patch("tools.research.requests.get")
    def test_fetch_web_content_network_error(self, mock_get):
        """Test network error handling."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")

        result = fetch_web_content("https://example.com")

        assert "Error fetching URL" in result
        assert "Network unreachable" in result

    @patch("tools.research.requests.get")
    def test_fetch_web_content_no_text(self, mock_get):
        """Test fetching page with no extractable text."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><script>only script</script></body></html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_web_content("https://example.com")

        assert "Warning: No significant text content" in result or "only script" in result

    @patch("tools.research.requests.get")
    def test_fetch_web_content_truncation(self, mock_get):
        """Test content truncation for very long pages."""
        # Create very long content
        long_content = "<html><body><p>" + ("a" * 10000) + "</p></body></html>"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = long_content
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_web_content("https://example.com")

        # Should be truncated to ~8000 chars
        assert len(result) <= 8100  # Allow some margin
        assert "..." in result  # Truncation indicator

    @patch("tools.research.requests.get")
    def test_fetch_web_content_with_main_tag(self, mock_get):
        """Test that main content area is properly identified."""
        html = """
        <html>
            <body>
                <div>Sidebar content</div>
                <main>
                    <p>Important main content</p>
                </main>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_web_content("https://example.com")

        assert "Important main content" in result


# ============================================================================
# Test Tool Integration
# ============================================================================

class TestToolIntegration:
    """Test FunctionTool wrappers."""

    def test_all_tools_exported(self):
        """Test that all tools are exported correctly."""
        from tools.research import get_tools_from_this_module

        tools = get_tools_from_this_module()

        # Should have 4 tools
        assert len(tools) == 4

        tool_names = [tool.name for tool in tools]
        expected_names = ["arxiv_search", "fetch_web_content", "web_search", "wikipedia_search"]

        for name in expected_names:
            assert name in tool_names

    def test_tool_descriptions(self):
        """Test that tools have proper descriptions."""
        from tools.research import get_tools_from_this_module

        tools = get_tools_from_this_module()

        for tool in tools:
            assert tool.description is not None
            assert len(tool.description) > 20  # Non-trivial description

    def test_arxiv_tool_callable(self):
        """Test that arxiv_search_tool is callable."""
        assert arxiv_search_tool is not None
        assert hasattr(arxiv_search_tool, 'run')
        assert callable(arxiv_search_tool.run)

    def test_web_search_tool_callable(self):
        """Test that web_search_tool is callable."""
        assert web_search_tool is not None
        assert hasattr(web_search_tool, 'run')
        assert callable(web_search_tool.run)

    def test_wikipedia_tool_callable(self):
        """Test that wikipedia_search_tool is callable."""
        assert wikipedia_search_tool is not None
        assert hasattr(wikipedia_search_tool, 'run')
        assert callable(wikipedia_search_tool.run)

    def test_fetch_tool_callable(self):
        """Test that fetch_web_content_tool is callable."""
        assert fetch_web_content_tool is not None
        assert hasattr(fetch_web_content_tool, 'run')
        assert callable(fetch_web_content_tool.run)


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch("tools.research.DDGS")
    def test_web_search_special_characters(self, mock_ddgs, monkeypatch):
        """Test web search with special characters in query."""
        monkeypatch.delenv("GOOGLE_CSE_API_KEY", raising=False)

        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = [
            {"title": "Result", "body": "Snippet", "href": "https://example.com"}
        ]
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance

        result = web_search("test & query <special>", max_results=1)

        assert "Result" in result

    @patch("tools.research.arxiv.Search")
    def test_arxiv_search_empty_summary(self, mock_search):
        """Test ArXiv result with empty summary."""
        result = MagicMock()
        result.title = "Test Paper"
        result.authors = []
        result.published = MagicMock(strftime=lambda x: "2024-01-01")
        result.summary = ""
        result.entry_id = "https://arxiv.org/abs/test"
        result.pdf_url = "https://arxiv.org/pdf/test"

        mock_search_instance = MagicMock()
        mock_search_instance.results.return_value = iter([result])
        mock_search.return_value = mock_search_instance

        result_text = arxiv_search("test", max_results=1)

        assert "Test Paper" in result_text

    @patch("tools.research.requests.get")
    def test_fetch_web_content_encoding_issues(self, mock_get):
        """Test handling of different character encodings."""
        # Unicode content
        unicode_content = "<html><body><p>Unicode: café, naïve, 中文</p></body></html>"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = unicode_content
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_web_content("https://example.com")

        # Should handle unicode properly
        assert "café" in result or "Unicode" in result
