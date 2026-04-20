# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A bootstrap of Knuth's original TeX from `tex.web` on modern Linux, **without** the Web2c / kpathsea / TeX Live toolchain. Free Pascal (`fpc`) is the candidate backend compiler; whether it is viable is the current open question.

The repo does **not** distribute Knuth's sources. They are fetched from CTAN (`sources` manifest) and verified against `checksums.sha256`.

## Non-negotiable rule

Canonical upstream files (`tex.web`, `tangle.web`, `weave.web`) are **never** edited in place. All local adaptation must live in change files (`*.ch`), build scripts, or helper tooling. `make verify` enforces the hashes, so in-place edits will fail verification.

## Pipeline

The Makefile drives a single linear pipeline:

```
fetch → verify → tangle → compile → taxonomy
```

- `fetch` reads URLs line-by-line from `sources`, skips files already present, uses `$(CURL)`.
- `verify` runs `sha256sum --check checksums.sha256` against the fetched `.web` files.
- `tangle` runs a bootstrap `$(TANGLE)` binary on `tex.web` to produce `tex.p` (+ `tex.pool`).
- `compile` runs `$(FPC) tex.p`, capturing stdout/stderr plus a header (timestamp, FPC version, command) and trailing exit code into `fpc.log`. The target intentionally preserves `fpc`'s non-zero exit — failure here is expected and is the subject of study.
- `taxonomy` runs `scripts/generate_taxonomy.py` over `fpc.log` using `taxonomy-rules.tsv` to emit `error-taxonomy.md`.

`make all` runs the whole chain; it lets `compile` fail but still runs `taxonomy` before exiting with `compile`'s return code. This is deliberate — the taxonomy is how we *understand* the failure.

Each phase has a `check-*-tools` prerequisite that verifies the corresponding binary (`curl`, `sha256sum`, `tangle`, `fpc`, `python3`) is on `$PATH`. Override any of these via `make CURL=... FPC=... TANGLE=...`.

## Common commands

```sh
make help          # list targets
make all           # full pipeline; compile failure is tolerated
make fetch         # download sources listed in `sources`
make verify        # check SHA-256 hashes
make tangle        # produce tex.p
make compile       # fpc tex.p → fpc.log (non-zero exit expected today)
make taxonomy      # regenerate error-taxonomy.md from fpc.log
make viewer        # serve progress viewer at http://127.0.0.1:8421
make clean         # remove fetched + generated root artifacts
```

There is no automated test suite. Reproducibility (matching hashes, stable `fpc.log` structure) is the current stand-in.

## Taxonomy tooling

`scripts/generate_taxonomy.py` parses FPC diagnostics with a fixed regex (`path(line,col) Level: message`), classifies each message against `taxonomy-rules.tsv`, and writes a grouped Markdown report. Rules are:

- tab-separated with exactly three fields: `pattern`, `category`, `notes`;
- matched case-insensitively with `re.search` against the message text;
- ordered — first match wins; everything else falls into `Unclassified`.

When new diagnostics appear in `fpc.log` they land under `Unclassified`. The usual fix is to add a row to `taxonomy-rules.tsv` — prefer a pattern narrow enough to carry a distinct category, not a catch-all.

## Project tracker

`project-tracker.json` is the live source of truth for action items, known errors, prompt sketches, and session notes. `todo.md` is a readable snapshot, not the canonical editor.

`scripts/progress_viewer.py` serves a single-page app over `http.server` on `127.0.0.1:8421` (`make viewer`). It has three endpoints:

- `GET /` — HTML app (inlined in the script).
- `GET /api/state` — returns `project-tracker.json`.
- `GET /api/artifact?path=…` — reads a file, but `resolve_artifact_path` refuses anything outside the repo root.
- `POST /api/state` — writes the tracker back; requires `version: 1`.

If editing the viewer, keep the path-escape guard and the version check — they're the only two safety rails.
