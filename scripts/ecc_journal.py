#!/usr/bin/env python3
"""
ecc_journal.py

Daily "error-correcting-code journal" pipeline:
  1. Query arXiv's official API for papers matching error-correcting-code
     keywords, submitted on a given day (default: today).
  2. For each paper, fetch its abstract-page HTML and scan for a GitHub
     repository link (in the "Comments" field or the abstract body —
     this is where authors conventionally put a code link).
  3. For papers WITH a detected repo: git-clone it (shallow clone) into
     repos/<arxiv_id>/.
  4. Write a Markdown journal entry for the day, split into two
     sections: "Papers with available code" (with a short summary of
     both the paper and what's in the cloned repo) and "Papers without
     available code" (paper summary only).

This is a genuinely standalone script -- it only needs `requests` and
`git` on PATH. It is NOT something Claude can run autonomously every
day (each conversation is a fresh session with no persistent
scheduler); it is meant to be scheduled by the user themselves, e.g.:

  # crontab -e, run every day at 08:00
  0 8 * * *  cd /path/to/ecc_journal && python3 scripts/ecc_journal.py

or as a GitHub Actions workflow on a `schedule:` trigger (see
ecc_journal.yml alongside this file for a ready-made example).

Usage:
    python3 ecc_journal.py                  # today, quant-ph + cs.IT
    python3 ecc_journal.py --date 2026-08-25
    python3 ecc_journal.py --categories quant-ph cs.IT
    python3 ecc_journal.py --max-results 100
"""

import argparse
import datetime
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ARXIV_API = "http://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

# Keywords that must appear (case-insensitive) in the title or abstract
# for a paper to count as "about error-correcting codes" -- deliberately
# a bit broad (catches both quantum and classical coding-theory work),
# tightened via CATEGORY_FILTER below.
ECC_KEYWORDS = [
    "error correcting code", "error-correcting code",
    "error correction code", "quantum error correction",
    "stabilizer code", "quantum code", "LDPC code",
    "surface code", "QEC",
]

GITHUB_URL_RE = re.compile(
    r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)"
)


def build_query(categories, start_date, end_date):
    """arXiv API query: (cat filter) AND (any ECC keyword in title/abs),
    restricted to a submission-date window (arXiv date filters are on
    the *v1 submission* timestamp, which is what we want for "papers
    published today")."""
    cat_clause = " OR ".join(f"cat:{c}" for c in categories)
    kw_clause = " OR ".join(
        f'(ti:"{kw}" OR abs:"{kw}")' for kw in ECC_KEYWORDS
    )
    date_clause = (
        f"submittedDate:[{start_date}0000 TO {end_date}2359]"
    )
    return f"({cat_clause}) AND ({kw_clause}) AND {date_clause}"


def fetch_arxiv(query, max_results=100, retries=3, pause=3.0):
    """Query the arXiv API and return a list of paper dicts. Retries
    on transient failures (arXiv's API occasionally 503s under load)."""
    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": str(max_results),
    }
    url = ARXIV_API + "?" + urllib.parse.urlencode(params)

    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = resp.read()
            break
        except Exception as e:
            last_err = e
            time.sleep(pause)
    else:
        raise RuntimeError(f"arXiv API request failed after {retries} tries: {last_err}")

    root = ET.fromstring(data)
    papers = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        arxiv_id_full = entry.find(f"{ATOM_NS}id").text.strip()
        arxiv_id = arxiv_id_full.rsplit("/", 1)[-1]
        title = entry.find(f"{ATOM_NS}title").text.strip().replace("\n", " ")
        summary = entry.find(f"{ATOM_NS}summary").text.strip().replace("\n", " ")
        authors = [a.find(f"{ATOM_NS}name").text
                   for a in entry.findall(f"{ATOM_NS}author")]
        comment_el = entry.find(f"{ARXIV_NS}comment")
        comment = comment_el.text.strip() if comment_el is not None and comment_el.text else ""
        published = entry.find(f"{ATOM_NS}published").text[:10]
        abs_url = arxiv_id_full.replace("/abs/", "/abs/")  # already an /abs/ URL
        pdf_url = None
        for link in entry.findall(f"{ATOM_NS}link"):
            if link.get("title") == "pdf":
                pdf_url = link.get("href")

        papers.append(dict(
            arxiv_id=arxiv_id, title=title, summary=summary,
            authors=authors, comment=comment, published=published,
            abs_url=abs_url, pdf_url=pdf_url,
        ))
    return papers


def find_github_repo(paper):
    """Look for a GitHub link in the comment field first (where authors
    conventionally put it), then fall back to scanning the abstract."""
    for field in (paper["comment"], paper["summary"]):
        m = GITHUB_URL_RE.search(field)
        if m:
            owner, repo = m.group(1), m.group(2).rstrip(".,)")
            return f"https://github.com/{owner}/{repo}"
    return None


def clone_repo(repo_url, dest_dir, timeout=120):
    """Shallow-clone a repo. Returns (success, message)."""
    if os.path.exists(dest_dir):
        return True, "already cloned"
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, dest_dir],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0:
            return True, "cloned"
        return False, result.stderr.strip()[-500:]
    except subprocess.TimeoutExpired:
        return False, "clone timed out"
    except Exception as e:
        return False, str(e)


def summarize_repo(repo_dir):
    """Cheap, dependency-free repo summary: README excerpt + top-level
    file listing + a guess at the primary language via file extensions.
    (A more sophisticated version could call an LLM here; kept simple
    and dependency-free so this script has zero non-stdlib requirements
    beyond `requests`-free urllib, which is already the case.)"""
    if not os.path.isdir(repo_dir):
        return "(repo directory not found)"

    entries = sorted(os.listdir(repo_dir))
    entries = [e for e in entries if not e.startswith(".git")]

    readme_excerpt = ""
    for candidate in ("README.md", "README.rst", "README.txt", "README"):
        path = os.path.join(repo_dir, candidate)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            readme_excerpt = text.strip().split("\n\n")[0][:600]
            break

    ext_counts = {}
    for root, _, files in os.walk(repo_dir):
        if ".git" in root:
            continue
        for fn in files:
            ext = os.path.splitext(fn)[1]
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1
    top_exts = sorted(ext_counts.items(), key=lambda x: -x[1])[:5]

    lines = [f"Top-level contents: {', '.join(entries[:15])}"]
    if top_exts:
        lines.append("Dominant file types: " + ", ".join(f"{e}({c})" for e, c in top_exts))
    if readme_excerpt:
        lines.append("README excerpt: " + readme_excerpt.replace("\n", " "))
    return "\n".join(lines)


def build_journal_entry(papers, repos_dir, date_str):
    """Returns the full Markdown text for one day's journal entry."""
    with_code, without_code = [], []
    for p in papers:
        repo_url = find_github_repo(p)
        if repo_url:
            dest = os.path.join(repos_dir, p["arxiv_id"])
            ok, msg = clone_repo(repo_url, dest)
            p["repo_url"] = repo_url
            p["clone_status"] = msg if ok else f"FAILED: {msg}"
            p["repo_summary"] = summarize_repo(dest) if ok else ""
            with_code.append(p)
        else:
            without_code.append(p)

    lines = [f"# Error-Correcting-Code Journal — {date_str}", ""]
    lines.append(f"Found **{len(papers)}** matching paper(s): "
                 f"**{len(with_code)}** with available code, "
                 f"**{len(without_code)}** without.")
    lines.append("")

    lines.append("## Papers with available code\n")
    if not with_code:
        lines.append("_None today._\n")
    for p in with_code:
        lines.append(f"### [{p['title']}]({p['abs_url']})")
        lines.append(f"**Authors:** {', '.join(p['authors'])}  ")
        lines.append(f"**arXiv:** {p['arxiv_id']} · **Published:** {p['published']}")
        lines.append(f"**Repository:** {p['repo_url']} ({p['clone_status']})\n")
        lines.append(f"**Summary:** {p['summary'][:500]}...\n")
        if p["repo_summary"]:
            lines.append("**Repository contents:**")
            lines.append("```")
            lines.append(p["repo_summary"])
            lines.append("```")
        lines.append("")

    lines.append("## Papers without available code\n")
    if not without_code:
        lines.append("_None today._\n")
    for p in without_code:
        lines.append(f"### [{p['title']}]({p['abs_url']})")
        lines.append(f"**Authors:** {', '.join(p['authors'])}  ")
        lines.append(f"**arXiv:** {p['arxiv_id']} · **Published:** {p['published']}\n")
        lines.append(f"**Summary:** {p['summary'][:500]}...\n")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Daily error-correcting-code arXiv journal")
    parser.add_argument("--date", default=None,
                         help="YYYY-MM-DD (default: today)")
    parser.add_argument("--categories", nargs="+",
                         default=["quant-ph", "cs.IT"],
                         help="arXiv categories to search (default: quant-ph cs.IT)")
    parser.add_argument("--max-results", type=int, default=100)
    parser.add_argument("--journal-dir", default="journal")
    parser.add_argument("--repos-dir", default="repos")
    args = parser.parse_args()

    date_str = args.date or datetime.date.today().isoformat()
    y, m, d = date_str.split("-")
    start_date = end_date = f"{y}{m}{d}"

    os.makedirs(args.journal_dir, exist_ok=True)
    os.makedirs(args.repos_dir, exist_ok=True)

    query = build_query(args.categories, start_date, end_date)
    print(f"Querying arXiv: {query}")
    papers = fetch_arxiv(query, max_results=args.max_results)
    print(f"Found {len(papers)} paper(s) for {date_str}.")

    entry_md = build_journal_entry(papers, args.repos_dir, date_str)
    out_path = os.path.join(args.journal_dir, f"{date_str}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(entry_md)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
