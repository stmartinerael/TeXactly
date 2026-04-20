# TeXactly

ur-TeX82 build: `tex.web` canonical source without the Web2c/kpathsea stack.

## What this is

Building Knuth's original TeX from its literate source (`tex.web`) on modern
Linux without the Web2c/kpathsea/TeX Live toolchain entirely.

## What this isn't

A TeX fork, a distribution, or a modified `tex.web`. Knuth's source is
canonical and untouched. Only change files, build scripts, and documentation
live here.

## Prerequisites

- Free Pascal (`fpc`)
- A bootstrap `tangle` binary (e.g. from `texlive-web` or equivalent)

## Fetching sources

This repo does not distribute Knuth's files. The authoritative upstream URLs
live in `sources`.

Fetch and verify them with `make fetch` and `make verify`, which check the
expected SHA-256 hashes:

```text
c62ab513ef167e93f71a23bd34f311e243210afd7c7a0f9b779614b71e398324  tex.web
60bb22ffeec81e10682ca903c2ccc5ba5c94eb9fe42387a01afc3173e681bf57  tangle.web
cfc60754a531e242407e184860ea3063f27f37f4e804e2ae0b27b50e29a8d352  weave.web
```

The checked-in `checksums.sha256` file is the source of truth used by `make
verify`.

## Build

```sh
make all
```

Useful individual targets:

- `make tangle` generates `tex.p`
- `make compile` runs `fpc tex.p` and captures output in `fpc.log`
- `make taxonomy` writes `error-taxonomy.md`
- `make viewer` starts the local progress viewer at `http://127.0.0.1:8421`
- `make clean` removes fetched and generated root-level artifacts

## Progress Viewer

The repo now includes a local one-page companion app for project tracking.

- Project-management source of truth: `project-tracker.json`
- Artifact contents stay canonical in their own files and are read live by the
  app
- Run locally with `make viewer`

Use it to:

- review known FPC failures,
- comment on current action items,
- browse tracked artifacts,
- sketch and save investigation prompts.

## Status

Phase 1 - Experimental. Current goal: a reproducible `tex.web` → `tex.p` →
`fpc` probe with a generated error taxonomy.  Free Pascal may or may not be
viable as the backend compiler — finding out is the point of this phase.

## License

Build scripts and change files in this repo: MIT.  `tex.web` and related files
are Knuth's, under his terms.
