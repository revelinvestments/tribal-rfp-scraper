"""Extract structured RFP records from page text using the Claude API.

The model reads the text of a Tribal procurement page and returns a JSON
array of solicitations. A --mock path is provided so the whole pipeline can
be tested without an API key.
"""

import json
import re

# Haiku is fast and inexpensive, which matters when this runs across ~30
# pages every day. You can override the model from the command line.
EXTRACTION_MODEL_DEFAULT = "claude-haiku-4-5-20251001"

# Tribal pages can be long. Cap the text we send so each call stays cheap.
MAX_PAGE_CHARS = 20000

SYSTEM_PROMPT = """You are a procurement analyst. You read the text of a \
Tribal government web page and identify every active or recent Request for \
Proposal (RFP), Request for Qualifications (RFQ), Invitation to Bid (ITB), or \
construction / development solicitation listed on it.

Return ONLY a JSON array. Each element must have exactly these keys:
- "title": the name of the solicitation (string)
- "posted_date": date posted in YYYY-MM-DD format, or "" if not shown
- "deadline": bid or response due date in YYYY-MM-DD format, or "" if not shown
- "project_type": one of "Housing", "Commercial", "Infrastructure", \
"Professional Services", "Other"
- "url": the most specific link to the RFP document or detail page, or "" \
if none is shown
- "summary": one sentence describing the scope of work (string)
- "confidence": "high", "medium", or "low" -- how sure you are this is a \
real, current solicitation

Rules:
- Only include construction, development, design, engineering, environmental, \
or professional-services solicitations. Ignore job postings, event notices, \
meeting minutes, and unrelated news.
- If the page lists no solicitations, return an empty array: []
- Do not invent data. Use "" for any field not present on the page.
- Return the JSON array and nothing else -- no explanation, no markdown."""


def build_user_prompt(tribe_name, page_text):
    """Assemble the user message for one page."""
    return (
        "Tribal government: %s\n\n"
        "Page text follows between triple backticks:\n\n"
        "```\n%s\n```" % (tribe_name, page_text[:MAX_PAGE_CHARS])
    )


def extract_rfps(tribe_name, page_text, client, model=EXTRACTION_MODEL_DEFAULT):
    """Call Claude to extract RFPs from one page.

    Returns (list_of_rfp_dicts, error_message_or_None).
    """
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user",
                       "content": build_user_prompt(tribe_name, page_text)}],
        )
    except Exception as exc:  # noqa: BLE001 - surface any API failure cleanly
        return [], "API error: %s" % exc

    raw = "".join(block.text for block in resp.content
                  if getattr(block, "type", None) == "text")
    rfps = parse_json_array(raw)
    if rfps is None:
        return [], "could not parse JSON from the model response"
    return rfps, None


def parse_json_array(raw):
    """Pull a JSON array out of a model response, tolerating stray text."""
    raw = (raw or "").strip()

    # Strip a ```json ... ``` fence if the model added one.
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()

    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Fallback: grab everything between the first [ and the last ].
    start, end = raw.find("["), raw.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(raw[start:end + 1])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    return None


def mock_extract(tribe_name, page_text):
    """Fake extraction for --mock mode. No API key or network needed.

    If the page text mentions an RFP-like keyword, it returns one obviously
    fake row so the rest of the pipeline can be tested end to end.
    Returns (list, error_or_None) to match extract_rfps().
    """
    lowered = page_text.lower()
    keywords = ("rfp", "request for proposal", "invitation to bid",
                "request for qualifications", "solicitation")
    if any(keyword in lowered for keyword in keywords):
        return [{
            "title": "[MOCK] Sample solicitation from %s" % tribe_name,
            "posted_date": "2026-05-01",
            "deadline": "2026-06-01",
            "project_type": "Housing",
            "url": "",
            "summary": ("Mock RFP generated for pipeline testing -- "
                        "not a real solicitation."),
            "confidence": "low",
        }], None
    return [], None
