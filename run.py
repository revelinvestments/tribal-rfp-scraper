#!/usr/bin/env python3
"""Tribal RFP Scraper -- entry point.

Fetches each Tribal procurement page listed in tribes.csv, extracts current
RFPs with the Claude API, and records which ones are new since the last run.

Examples
--------
    python run.py                 scrape every tribe in tribes.csv
    python run.py --mock          test run with fake extraction (no API key)
    python run.py --limit 3       only the first 3 tribes
    python run.py --tribe Oneida  only tribes whose name contains "Oneida"

Outputs land in the data/ folder:
    data/new_rfps.csv   solicitations found that are NEW since last run
    data/all_rfps.csv   cumulative master list of every unique solicitation
    data/seen.json      internal memory of what has been seen before
    data/run_log.txt    a per-tribe summary of the most recent run
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime

from scraper.fetch import fetch_page
from scraper.extract import extract_rfps, mock_extract, EXTRACTION_MODEL_DEFAULT
from scraper.store import (load_state, save_state, split_new,
                           write_csv, append_csv)

HERE = os.path.dirname(os.path.abspath(__file__))
TRIBES_CSV = os.path.join(HERE, "tribes.csv")
DATA_DIR = os.path.join(HERE, "data")
STATE_PATH = os.path.join(DATA_DIR, "seen.json")
ALL_CSV = os.path.join(DATA_DIR, "all_rfps.csv")
NEW_CSV = os.path.join(DATA_DIR, "new_rfps.csv")
LOG_PATH = os.path.join(DATA_DIR, "run_log.txt")


def load_env():
    """Load ANTHROPIC_API_KEY from a .env file if one exists."""
    env_path = os.path.join(HERE, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def load_tribes():
    """Read tribes.csv, keeping only rows that have an rfp_url."""
    with open(TRIBES_CSV, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if (row.get("rfp_url") or "").strip()]


def build_client(model):
    """Create an Anthropic API client, or exit with a helpful message."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        sys.exit("ERROR: ANTHROPIC_API_KEY is not set.\n"
                 "Add it to a .env file (see .env.example), or run with "
                 "--mock to test the pipeline without a key.")
    try:
        from anthropic import Anthropic
    except ImportError:
        sys.exit("ERROR: the 'anthropic' package is not installed.\n"
                 "Run:  pip install -r requirements.txt")
    return Anthropic(api_key=api_key)


def parse_args():
    parser = argparse.ArgumentParser(description="Tribal RFP Scraper")
    parser.add_argument("--mock", action="store_true",
                        help="use fake extraction; no API key needed")
    parser.add_argument("--limit", type=int, default=0,
                        help="only scrape the first N tribes")
    parser.add_argument("--tribe", type=str, default="",
                        help="only scrape tribes whose name contains this text")
    parser.add_argument("--model", type=str, default=EXTRACTION_MODEL_DEFAULT,
                        help="Claude model to use for extraction")
    return parser.parse_args()


def main():
    args = parse_args()
    load_env()

    tribes = load_tribes()
    if args.tribe:
        tribes = [t for t in tribes if args.tribe.lower() in t["name"].lower()]
    if args.limit:
        tribes = tribes[:args.limit]
    if not tribes:
        sys.exit("No tribes to scrape. Check tribes.csv and your filters.")

    client = None if args.mock else build_client(args.model)

    state = load_state(STATE_PATH)
    all_found = []
    log_lines = []
    mode = "MOCK MODE" if args.mock else ("model " + args.model)
    print("Scraping %d tribe(s) -- %s\n" % (len(tribes), mode))

    for index, tribe in enumerate(tribes, 1):
        name = tribe["name"]
        url = tribe["rfp_url"].strip()
        print("[%d/%d] %s" % (index, len(tribes), name))

        result = fetch_page(url)
        if not result["ok"]:
            print("  fetch failed: %s" % result["error"])
            log_lines.append("%s: FETCH FAIL - %s" % (name, result["error"]))
            continue
        if result["js_warning"]:
            print("  warning: very little text returned "
                  "(page may need JavaScript rendering)")
            log_lines.append("%s: JS WARNING - little text returned" % name)

        if args.mock:
            rfps, error = mock_extract(name, result["text"])
        else:
            rfps, error = extract_rfps(name, result["text"], client, args.model)
            time.sleep(1)  # be polite to the API

        if error:
            print("  extraction error: %s" % error)
            log_lines.append("%s: EXTRACT ERROR - %s" % (name, error))
            continue

        for rfp in rfps:
            rfp["tribe"] = name
            rfp["state"] = tribe.get("state", "")
            rfp["source_page"] = url
            if not (rfp.get("url") or "").strip():
                rfp["url"] = url
        all_found.extend(rfps)
        print("  found %d solicitation(s)" % len(rfps))
        log_lines.append("%s: %d found" % (name, len(rfps)))

    new, known = split_new(all_found, state)
    save_state(STATE_PATH, state)
    append_csv(ALL_CSV, new)   # master list grows only with genuinely new rows
    write_csv(NEW_CSV, new)    # this run's new finds (overwritten each run)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as handle:
        handle.write("Run at %s\n" % datetime.now().isoformat(timespec="seconds"))
        handle.write("Tribes scraped: %d\n" % len(tribes))
        handle.write("Total solicitations found: %d\n" % len(all_found))
        handle.write("New since last run: %d\n\n" % len(new))
        handle.write("\n".join(log_lines) + "\n")

    print("\n" + "=" * 52)
    print("Done. %d solicitation(s) found, %d NEW since last run."
          % (len(all_found), len(new)))
    print("  New RFPs:    data/new_rfps.csv")
    print("  Master list: data/all_rfps.csv")
    print("  Run log:     data/run_log.txt")
    if new:
        print("\nNEW THIS RUN:")
        for record in new:
            print("  - [%s] %s" % (record["tribe"], record["title"]))


if __name__ == "__main__":
    main()
