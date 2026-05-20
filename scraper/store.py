"""Deduplication, state tracking, and CSV output.

The scraper remembers which RFPs it has already seen (data/seen.json) so that
each run can tell you exactly what is NEW. That "new since last run" signal is
the core value of the tool.
"""

import csv
import json
import hashlib
import os
from datetime import date

# Column order for both CSV outputs.
CSV_FIELDS = [
    "first_seen", "tribe", "state", "title", "posted_date", "deadline",
    "project_type", "confidence", "url", "summary", "source_page",
]


def rfp_hash(tribe, rfp):
    """A stable fingerprint for one RFP, used to detect duplicates."""
    basis = "%s|%s|%s" % (
        tribe,
        (rfp.get("title", "") or "").strip().lower(),
        (rfp.get("url", "") or "").strip(),
    )
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def load_state(path):
    """Load the seen-RFP fingerprints. Returns {} if there is no state yet."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    return {}


def save_state(path, state):
    """Write the seen-RFP fingerprints back to disk."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)


def split_new(records, state):
    """Split records into (new, already_known).

    Each record must carry a "tribe" key plus the RFP fields. This also
    stamps every record with a "first_seen" date and updates `state`.
    """
    new, known = [], []
    today = date.today().isoformat()
    for record in records:
        fingerprint = rfp_hash(record["tribe"], record)
        if fingerprint in state:
            record["first_seen"] = state[fingerprint]
            known.append(record)
        else:
            state[fingerprint] = today
            record["first_seen"] = today
            new.append(record)
    return new, known


def write_csv(path, records):
    """Overwrite a CSV with exactly these records (plus a header)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS,
                                extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def append_csv(path, records):
    """Append records to a CSV, creating it with a header if needed."""
    if not records:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS,
                                extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        for record in records:
            writer.writerow(record)
