"""Fetch Tribal RFP pages and convert them to clean, link-annotated text.

The text produced here is what gets sent to the Claude API for extraction.
Hyperlinks are kept inline as "link text (LINK: https://...)" so the model
can capture the actual URL of each RFP document.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# A normal browser User-Agent. Some Tribal sites block obvious bots.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0 Safari/537.36"
)


def fetch_page(url, timeout=30):
    """Fetch a single URL.

    Returns a dict with:
      ok          True if the page was fetched and parsed
      status      HTTP status code (or None on a network error)
      text        cleaned, link-annotated page text
      error       error message, or None
      js_warning  True if the page returned almost no text (likely needs
                  JavaScript rendering, which this MVP does not do)
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        return {"ok": False, "status": None, "text": "",
                "error": str(exc), "js_warning": False}

    if resp.status_code != 200:
        return {"ok": False, "status": resp.status_code, "text": "",
                "error": "HTTP %s" % resp.status_code, "js_warning": False}

    text = html_to_text(resp.text, url)
    return {"ok": True, "status": 200, "text": text, "error": None,
            "js_warning": len(text.strip()) < 200}


def html_to_text(html, base_url):
    """Convert raw HTML to readable text, keeping links annotated inline."""
    soup = BeautifulSoup(html, "lxml")

    # Drop everything that is not content.
    for tag in soup(["script", "style", "noscript", "svg", "header",
                     "footer", "nav"]):
        tag.decompose()

    # Replace each link with "text (LINK: absolute_url)" so the model
    # sees both the label and the real destination.
    for anchor in soup.find_all("a", href=True):
        href = (anchor.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = urljoin(base_url, href)
        label = anchor.get_text(" ", strip=True)
        anchor.replace_with("%s (LINK: %s)" % (label, absolute))

    text = soup.get_text("\n", strip=True)
    # Collapse blank lines so the model gets a tidy block of text.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
