# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project goal

Build Knuth's ur-TeX82 from its canonical literate source (`tex.web`) on modern Linux using Free Pascal (`fpc`) — no Web2c, kpathsea, or TeX Live toolchain. This repo contains only change files, build scripts, and documentation. Knuth's source files are never committed here.

## Build

```sh
make
```

## Prerequisites

- `fpc` (Free Pascal — `sudo dnf install fpc` on Fedora)
- System `tangle` binary (`/usr/bin/tangle` from `texlive-web` package)

## Sources

Knuth's files are not committed here. Run `make fetch` to download them from CTAN, or `make verify` to check checksums after a manual download.

## Pipeline

`tex.web` → `tangle` → `tex.p` (Pascal) → `fpc` → native binary

Current phase: cataloguing `fpc` errors when compiling the tangled `tex.p`.

## What belongs in this repo

- Change files (`.ch`) patching `tex.web` for the target platform
- `Makefile` and build scripts
- Documentation

Do not commit `tex.web`, `tangle.web`, generated `.p` files, or compiled binaries.
