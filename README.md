# TeXactly

ur-TeX82 build: `tex.web` canonical source without the Web2c/kpathsea stack.

## What this is

Building Knuth's original TeX from its literate source (`tex.web`) on modern Linux without the Web2c/kpathsea/TeX Live toolchain entirely.

## What this isn't

A TeX fork, a distribution, or a modified `tex.web`. Knuth's source is
canonical and untouched. Only change files, build scripts, and documentation
live here.

## Prerequisites

- Free Pascal (`fpc`)
- A bootstrap `tangle` binary (e.g. from `texlive-web` or equivalent)

## Fetching sources

This repo does not distribute Knuth's files. Grab them yourself:

```
curl -O https://mirrors.ctan.org/systems/knuth/dist/tex/tex.web
curl -O https://mirrors.ctan.org/systems/knuth/dist/web/tangle.web
```

Expected checksums (SHA-256):

```
60bb22ffeec81e10682ca903c2ccc5ba5c94eb9fe42387a01afc3173e681bf57  tangle.web
c62ab513ef167e93f71a23bd34f311e243210afd7c7a0f9b779614b71e398324  tex.web
```

## Build

```
make
```

## Status

Experimental. Current goal: `tex.web` → `tex.p` → `fpc` error taxonomy.
Free Pascal may or may not be viable as the backend compiler — finding out
is the point of this phase.

## License

Build scripts and change files in this repo: MIT.
`tex.web` and related files are Knuth's, under his terms.
