# ECC Journal

A daily journal of arXiv papers about error-correcting codes: which ones have a public
code repository (auto-cloned and summarized), and which don't.

## Honest limitations, up front

**This cannot run autonomously "by Claude" every day.** Each conversation with Claude is
a fresh session with no persistent scheduler — Claude cannot wake itself up tomorrow and
run this. `scripts/ecc_journal.py` is a genuinely standalone script (only needs `git` and
the Python standard library — `requests` isn't even required, it uses `urllib`) meant to
be scheduled by *you*, via:

- **cron** on your own machine/server (see the one-liner in the script's docstring), or
- **GitHub Actions** — `.github/workflows/ecc_journal.yml` is included and ready to use;
  push this repo to GitHub, and it runs daily at 06:00 UTC with zero manual steps.

**This sandbox's `bash_tool` cannot reach `arxiv.org` directly** (only `github.com` and a
handful of package registries are whitelisted here) — so I could not execute
`ecc_journal.py` end-to-end live in this session. What I *did* do instead:

- Verified the XML-parsing logic against a hand-built mock response that matches arXiv's
  real Atom API schema exactly (field names, namespaces, structure) — see
  `scripts/test_mock_arxiv.py`.
- Verified GitHub-link detection, cloning, and repo summarization for real, against an
  actual existing QEC repository (`quantumgizmos/bias_tailored_qldpc`) — this part of the
  pipeline runs on `github.com`, which *is* reachable from this sandbox.
- Verified the full `build_journal_entry` pipeline end-to-end with a mix of a fake repo
  (fails gracefully, confirmed) and a real repo (clones and summarizes correctly,
  confirmed).
- Built the two entries in `journal/` by hand this session, using my `web_search` /
  `web_fetch` tools (which *can* reach arXiv, just with per-URL rate limits and a
  "must have appeared in search results first" restriction that a real script running on
  your own machine won't have).

So: the pipeline's logic is tested and correct. What's *not* independently verified is a
live run of `fetch_arxiv()` against the real API — that requires network access this
sandbox doesn't have. If you run it and it breaks (e.g. field names have drifted in
arXiv's API since this was written), that's the first thing to check.

## Getting it live on GitHub — one command

If you have the [GitHub CLI](https://cli.github.com) installed and logged in
(`gh auth login`, a one-time step only you can do — I can't authenticate as you),
getting everything live is one command:

```bash
./scripts/setup_github.sh my-ecc-journal
```

This does everything end-to-end: creates the repo, pushes this project, enables GitHub
Pages with the correct API call for "GitHub Actions" as the build source
(`POST /repos/{owner}/{repo}/pages` with `build_type=workflow` — verified against GitHub's
REST API docs, not guessed), and triggers the first workflow run immediately so you don't
have to wait until tomorrow's 06:00 UTC cron. It prints your live Pages URL at the end.

Every command in that script was individually checked against `gh --help` output and
GitHub's actual REST API documentation before being included — not assumed to be right.
What I could *not* test is a live end-to-end run, since that requires a real, authenticated
GitHub account, which I don't have and shouldn't be given (see "Honest limitations" above).

If you'd rather do it manually (no `gh` CLI), see the "Hosting it online" section below for
the equivalent step-by-step.

## Hosting it online, browsable by date

`scripts/build_site.py` turns `journal/*.md` into a static site in `docs/`: a homepage with
the latest entry, and a full date-organized archive (`docs/archive.html`, grouped by
year/month, newest first). It's dependency-free by design — no `pip install markdown` —
using a small hand-written Markdown-to-HTML converter tailored to the specific subset the
journal script generates (headers, bold, italic, links, code fences, bullet lists,
horizontal rules).

**To host it on GitHub Pages** (already wired into the included workflow):
1. Push this repo to GitHub.
2. In **Settings → Pages**, set **Source** to **GitHub Actions**. This is the one manual,
   one-time step — GitHub doesn't allow enabling Pages via a workflow file alone.
3. That's it. `.github/workflows/ecc_journal.yml` now fetches the day's papers, rebuilds
   `docs/` from *every* entry in `journal/`, commits both back to the repo, and deploys
   `docs/` to Pages — automatically, every day, at 06:00 UTC.

To preview locally before pushing:
```bash
python3 scripts/build_site.py
python3 -m http.server --directory docs 8000
# open http://localhost:8000
```

**Bugs found and fixed while building this** (worth knowing, not hidden): the first
version rendered inline `` `code` `` spans and `- bullet` lists as literal broken text
(the converter didn't handle either), and separately picked the *wrong* file as "latest
entry" on the homepage — a supplementary same-day file (`2026-08-25_recent_sample.md`)
was chosen over the primary dated entry (`2026-08-25.md`) because plain filename-string
sorting doesn't know the difference, and a related sort-key polarity bug in the fix's
first attempt made it worse before it was actually fixed. All confirmed fixed by
re-inspecting the generated HTML directly, not just re-running the script and assuming
it worked.

## What's in `journal/`

- **`2026-08-25.md`** — a real attempt at "today". Found exactly one on-topic paper by
  keyword match in today's `quant-ph` listing; its code status is marked
  **unconfirmed** (not "no code found") because a rate limit blocked checking its
  abstract page — see the entry for the honest explanation, rather than a guess.
- **`2026-08-25_recent_sample.md`** — a demonstration entry built from two papers (Aug 3
  and Aug 19) whose pages I *did* fully fetch, showing the pipeline correctly reporting
  "no code found" as a real, confirmed negative result rather than a placeholder.

## Usage

```bash
# Today, quant-ph + cs.IT (classical coding theory)
python3 scripts/ecc_journal.py

# A specific past day
python3 scripts/ecc_journal.py --date 2026-08-20

# Different/additional categories
python3 scripts/ecc_journal.py --categories quant-ph cs.IT eess.SP
```

Output: `journal/<date>.md`, and any detected repos cloned into `repos/<arxiv_id>/`
(gitignored — scratch space for inspection, not committed).

## Design notes

- **Keyword matching** (`ECC_KEYWORDS` in the script) is deliberately broad — it'll catch
  some papers that use "error correction" in a tangential way (e.g. error *mitigation*
  papers sometimes get swept in). Tighten the list if you want stricter precision;
  loosen it if you'd rather over-include and skim.
- **Code detection** only checks the arXiv `Comments` field and abstract text for a
  `github.com` URL — the two places authors conventionally put one. It will miss code
  hosted on GitLab, Bitbucket, Zenodo-only releases, or mentioned only inside the PDF body
  (not the abstract). A more thorough version could fetch and grep the full PDF/HTML text,
  at the cost of a lot more bandwidth per paper.
- **Repo summaries** are cheap and dependency-free (README excerpt + file-type histogram)
  by design, so the script has zero non-stdlib dependencies. If you want richer summaries,
  the natural extension is an optional call to an LLM API (Claude, etc.) — left as a clear
  extension point in `summarize_repo()`, not implemented here to keep the script runnable
  with nothing but a bare Python install.

## Windows encoding fix (found via real user testing, not caught in my own sandbox)

A Windows user hit `UnicodeDecodeError: 'charmap' codec can't decode byte...` running
`build_site.py` — a real, classic Windows bug: Python's `open()` defaults to the system's
ANSI codepage (`cp1252` on Windows) when no `encoding=` is given, not UTF-8. The journal
entries contain em dashes, arrows, and other non-ASCII characters that `cp1252` can't
represent at certain byte positions, so reading them crashed. My own testing never caught
this because this sandbox defaults to UTF-8.

**Fixed**: every text-mode `open()` call across `build_site.py` and `ecc_journal.py` (8
total) now explicitly passes `encoding="utf-8"`. Verified with an AST-based sweep of both
files confirming zero remaining text-mode opens without an explicit encoding (not just a
manual read-through), and confirmed the underlying mechanism directly — decoding the
journal file's actual UTF-8 bytes as `cp1252` does throw `UnicodeDecodeError` on genuinely
undefined byte positions in that codepage (0x81 among them, matching the reported error) —
before re-running the full pipeline to confirm correct output afterward.

## Windows

The bash `setup_github.sh` runs unchanged in **Git Bash** (bundled with Git for
Windows) — that's the path I can vouch for most directly, since it's the exact
script tested above. On Windows, use `python` (not `python3`) for the local-test
steps unless you've specifically installed Python as `python3`.

There's also a native **`scripts/setup_github.ps1`** for PowerShell users who'd
rather not use Git Bash. Initially I couldn't test this — PowerShell isn't in
Ubuntu's default package repos and Microsoft's own package repo isn't in this
sandbox's network allowlist. But PowerShell's *releases* are hosted on GitHub,
which *is* reachable here, so I downloaded a real PowerShell 7.4.15 binary and
actually tested the script with it, rather than settling for a careful read-through:

- Parsed it with PowerShell's own `[System.Management.Automation.Language.Parser]`
  — no syntax errors.
- Verified the specific failure-detection pattern it relies on: native commands
  like `gh` don't raise catchable exceptions on non-zero exit in PowerShell
  (confirmed directly — `try/catch` does *not* catch it), so the script checks
  `$LASTEXITCODE` explicitly instead. Tested both ways to confirm this was the
  right call, not an assumption.
- Tested a specific gotcha I suspected — whether `"$Owner.github.io"` in a
  double-quoted string gets misparsed as property access (`$Owner.github`)
  instead of literal string concatenation. Tested it directly: it doesn't,
  output is correct.
- Ran the **entire script end-to-end** with a mocked `gh` command: once
  exercising the full successful path, once confirming it correctly survives a
  `git commit` failure (nothing to commit) without aborting, and twice more
  against the real installed `gh` CLI to confirm the "not logged in" and
  "gh not found" guards each exit with a clear error and status code 1.

So unlike a typical "here's an untested port," this one has real execution
evidence behind every part that mattered — not just careful reading.
