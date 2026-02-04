# Firecrawl Python SDK - Quick Start Guide

> **Version:** 1.x
> **Last Updated:** October 2024

Turn any website into clean, LLM-ready markdown with Firecrawl.

## Installation

```bash
pip install firecrawl-py
```

## Quick Start

```python
from firecrawl import FirecrawlApp

# Initialize the client
app = FirecrawlApp(api_key="fc-YOUR-API-KEY")

# Scrape a single URL
result = app.scrape_url("https://example.com")
print(result["markdown"])
```

## Core Methods

### `scrape_url()`

Scrape a single URL and get its content.

```python
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key="fc-YOUR-API-KEY")

# Basic scrape
result = app.scrape_url("https://docs.firecrawl.dev")

# With options
result = app.scrape_url(
    "https://docs.firecrawl.dev",
    params={
        "formats": ["markdown", "html"],
        "onlyMainContent": True
    }
)

print(result["markdown"])
```

**Parameters:**
- `url` (str): The URL to scrape
- `params` (dict, optional): Scrape options
  - `formats`: List of output formats ("markdown", "html", "rawHtml")
  - `onlyMainContent`: Remove headers/footers (default: True)

**Returns:** Dictionary with `markdown`, `html`, `metadata`

---

### `crawl_url()`

Crawl an entire website starting from a URL.

```python
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key="fc-YOUR-API-KEY")

# Crawl a site
result = app.crawl_url(
    "https://docs.firecrawl.dev",
    params={
        "maxDepth": 2,
        "limit": 10,
        "ignoreSitemap": True
    }
)

for page in result:
    print(page["metadata"]["title"])
```

**Parameters:**
- `url` (str): Starting URL
- `params` (dict, optional): Crawl options
  - `maxDepth`: How deep to crawl (default: 2)
  - `limit`: Maximum pages to crawl
  - `ignoreSitemap`: Skip sitemap discovery (default: False)
  - `allowBackwardCrawling`: Allow crawling parent paths

**Returns:** List of page results

---

### `async_crawl_url()`

Start an async crawl job for large sites.

```python
from firecrawl import FirecrawlApp
import time

app = FirecrawlApp(api_key="fc-YOUR-API-KEY")

# Start async crawl
job = app.async_crawl_url(
    "https://docs.firecrawl.dev",
    params={"maxDepth": 3, "limit": 100}
)

job_id = job["jobId"]
print(f"Started crawl job: {job_id}")

# Poll for completion
while True:
    status = app.check_crawl_status(job_id)
    if status["status"] == "completed":
        break
    print(f"Progress: {status['completed']}/{status['total']}")
    time.sleep(5)

# Get results
print(f"Crawled {len(status['data'])} pages")
```

---

### `map_url()`

Discover all URLs on a website without scraping content.

```python
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key="fc-YOUR-API-KEY")

# Map a website
urls = app.map_url("https://firecrawl.dev")

print(f"Found {len(urls)} URLs:")
for url in urls[:10]:
    print(f"  - {url}")
```

**Parameters:**
- `url` (str): The website to map
- `params` (dict, optional): Map options
  - `search`: Filter URLs by keyword
  - `limit`: Maximum URLs to return

**Returns:** List of discovered URLs

---

## Complete Example

```python
from firecrawl import FirecrawlApp

def scrape_documentation(base_url: str, api_key: str) -> list[dict]:
    """Scrape all pages from a documentation site."""

    app = FirecrawlApp(api_key=api_key)

    # First, map the site to find all URLs
    all_urls = app.map_url(base_url, params={"limit": 50})

    # Then crawl with depth limit
    results = app.crawl_url(
        base_url,
        params={
            "maxDepth": 2,
            "limit": 20,
            "ignoreSitemap": True
        }
    )

    return results

# Usage
docs = scrape_documentation(
    "https://docs.example.com",
    "fc-YOUR-API-KEY"
)
```

## Error Handling

```python
from firecrawl import FirecrawlApp
from firecrawl.exceptions import FirecrawlError

app = FirecrawlApp(api_key="fc-YOUR-API-KEY")

try:
    result = app.scrape_url("https://example.com")
except FirecrawlError as e:
    print(f"Scrape failed: {e}")
```

## Rate Limits

- Free tier: 500 credits/month
- Scrape: 1 credit per page
- Crawl: 1 credit per page crawled

---

*For full documentation, visit [docs.firecrawl.dev](https://docs.firecrawl.dev)*
