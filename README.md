# Tribal RFP Scraper

A tool that checks Tribal government websites every day, finds new construction
and development RFPs, and tells you which ones are new since the last check.

This is the engine behind the Tribal Council platform. It currently covers
**35 Tribes across Minnesota, Wisconsin, Michigan, and Iowa** — your anchor
region.

---

## What it does

1. Reads a list of Tribes and their RFP/procurement page URLs (`tribes.csv`).
2. Visits each page and pulls out the text.
3. Sends that text to Claude, which extracts every solicitation it finds —
   title, dates, project type, and a link.
4. Compares the results against everything it has seen before, so you get a
   clean list of **what is NEW today**.
5. Writes everything to spreadsheet files in the `data/` folder.

It can run on your computer when you want, or automatically every morning in
the cloud (free) — both are explained below.

---

## What you need

- **Python 3.10 or newer** — free, from [python.org/downloads](https://www.python.org/downloads/).
  During install on Windows, check the box **"Add Python to PATH"**.
- **An Anthropic API key** — from [console.anthropic.com](https://console.anthropic.com/)
  under Settings → API Keys. This is what lets the tool read pages with AI.
- **A GitHub account** (free) — only needed for the automatic daily runs in Part 2.

You do not need to be a programmer. Every step is copy-and-paste.

---

## Part 1 — Run it on your computer

### Step 1: Open a terminal in this folder

- **Windows:** open this `tribal-rfp-scraper` folder in File Explorer, click the
  address bar, type `cmd`, and press Enter.
- **Mac:** right-click the folder and choose "New Terminal at Folder".

### Step 2: Install the dependencies

Paste this and press Enter:

```
pip install -r requirements.txt
```

### Step 3: Do a test run (no API key needed yet)

```
python run.py --mock
```

This uses fake data to prove the plumbing works. You should see it visit each
Tribe and write files into the `data/` folder. If that worked, you are ready
for the real thing.

> Note: a test run on this computer talks to live Tribal websites. If your
> internet or a firewall blocks it, you'll see "fetch failed" lines — that is
> the tool handling errors gracefully, not a crash.

### Step 4: Add your API key

1. Find the file named `.env.example` in this folder.
2. Make a copy of it and rename the copy to exactly **`.env`** (no other name).
3. Open `.env` in Notepad and replace the placeholder with your real key.
4. Save and close. Your key stays on your computer — it is never uploaded.

### Step 5: A real run on a few Tribes

```
python run.py --limit 3
```

This scrapes the first 3 Tribes for real. Check `data/new_rfps.csv` to see
what it found.

### Step 6: The full run

```
python run.py
```

This scrapes all 35 Tribes. It takes a couple of minutes.

**Useful options:**

| Command | What it does |
|---|---|
| `python run.py` | Scrape every Tribe in `tribes.csv` |
| `python run.py --mock` | Test run, no API key, no cost |
| `python run.py --limit 5` | Only the first 5 Tribes |
| `python run.py --tribe Oneida` | Only Tribes whose name contains "Oneida" |

---

## Reading the output

Everything lands in the `data/` folder:

- **`new_rfps.csv`** — solicitations that are NEW since the last run. This is
  the file that matters day to day — it is your daily digest.
- **`all_rfps.csv`** — the master list of every unique solicitation ever found.
- **`run_log.txt`** — a per-Tribe summary of the most recent run (how many
  found, any errors, any pages that need attention).
- **`seen.json`** — the tool's memory of what it has already seen. Do not edit
  or delete this, or everything will look "new" again.

Open the `.csv` files in Excel or import them into Google Sheets.

---

## Part 2 — Run it automatically every day (free)

GitHub can run this scraper for you every morning at no cost. You do not need
to leave your computer on.

### Step 1: Create a GitHub repository

1. Sign in at [github.com](https://github.com/) (create a free account if needed).
2. Click the **+** in the top right → **New repository**.
3. Name it something like `tribal-rfp-scraper`. Set it to **Public**
   (public repos get unlimited free automation minutes).
4. Click **Create repository**.

### Step 2: Upload these files

On the new repository page, click **uploading an existing file**, then drag in
everything from this folder. Commit the upload.

> Do not upload your `.env` file. It is excluded automatically by `.gitignore`,
> and your API key goes in as a secret instead — see the next step.

### Step 3: Add your API key as a secret

1. In the repository, go to **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**.
3. Name: `ANTHROPIC_API_KEY` (exactly that).
4. Value: paste your real API key.
5. Click **Add secret**.

### Step 4: Turn it on

Go to the **Actions** tab and enable workflows if prompted. From then on the
scraper runs **every day at 6:00 AM Central**. You can also trigger it any
time: Actions → "Tribal RFP Scraper" → **Run workflow**.

Each run updates `data/new_rfps.csv` and `data/all_rfps.csv` right in the
repository, so your history builds up automatically.

To change the schedule, edit the `cron` line in
`.github/workflows/scrape.yml` (the time is in UTC).

---

## Connect it to your Google Sheet

The simplest way to see results in your RFP Tracker, with no extra setup:

1. In your RFP Tracker, add a new tab called **Scraper Feed**.
2. In cell A1 of that tab, paste this formula (swap in your GitHub username
   and repo name):

   ```
   =IMPORTDATA("https://raw.githubusercontent.com/YOUR-USERNAME/tribal-rfp-scraper/main/data/all_rfps.csv")
   ```

3. The tab now mirrors the scraper's master list and refreshes on its own.

Keep your hand-curated **Active RFPs** tab separate — review items on the
Scraper Feed tab and copy the real ones over. The AI extraction is good but not
perfect, so a human glance before anything reaches a paying GC is worth it.

---

## Maintaining it

**`tribes.csv` is yours to edit.** It has five columns: `name`, `state`,
`homepage`, `rfp_url`, `notes`. To add a Tribe, add a row. To fix a scraper
that finds nothing, the `rfp_url` is usually the thing to correct.

**8 Tribes still need a real RFP page URL.** They are marked in the `notes`
column of `tribes.csv` as "needs research" — their `rfp_url` currently points
at the homepage as a fallback. When you find the real procurement page,
replace the URL.

**Shakopee Mdewakanton** has no public RFP page at all — likely a closed,
invited-bidder process. That is flagged in `tribes.csv`; a phone call to their
procurement office is the way to confirm.

**Check `run_log.txt` after runs.** Lines marked `JS WARNING` mean a page
returned almost no text — usually because it builds itself with JavaScript.
Those pages need the upgrade described below.

---

## What it costs

The scraper uses the Claude Haiku model, which is inexpensive. Scraping ~30
pages once a day is on the order of **a few dollars a month** — almost
certainly under $10. Check current pricing at
[console.anthropic.com](https://console.anthropic.com/). Running with `--mock`
costs nothing.

---

## Known limitations and Phase 2 upgrades

This is a deliberately lean first version. Planned upgrades, roughly in order:

- **JavaScript-rendered pages.** A few Tribal sites build their content with
  JavaScript and return little text to a simple fetch. Adding a headless
  browser (Playwright) fixes this. Watch for `JS WARNING` in `run_log.txt`.
- **Reading inside PDFs.** Right now the tool reads the listing page and
  captures PDF links, but does not open the PDFs. Downloading and reading them
  would add deadlines and dollar values that only appear inside the document.
- **Writing straight into Google Sheets.** The `IMPORTDATA` method above works
  with zero setup; a direct write is possible later with a Google service
  account.
- **More regions.** Adding rows to `tribes.csv` for other regions is all it
  takes to expand beyond the Midwest.

---

## File reference

| File | Purpose |
|---|---|
| `run.py` | The script you run. Start here. |
| `tribes.csv` | The list of Tribes and their RFP page URLs. Edit this. |
| `scraper/fetch.py` | Downloads a page and cleans it into text. |
| `scraper/extract.py` | Asks Claude to pull RFPs out of the text. |
| `scraper/store.py` | Tracks what is new and writes the CSV files. |
| `requirements.txt` | The Python packages the tool needs. |
| `.env.example` | Template for your API key. Copy to `.env`. |
| `.github/workflows/scrape.yml` | The daily automatic-run schedule. |
| `data/` | Where results are written. |
