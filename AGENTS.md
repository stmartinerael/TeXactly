# Repository Guidelines

## Project Structure & Module Organization

This repository is intentionally small. [`README.md`](/home/erevanil/src/TeXactly/README.md) describes the project goal: build Knuth's original `tex.web` on modern Linux without the Web2c/kpathsea stack. [`sources`](/home/erevanil/src/TeXactly/sources) is a source manifest listing the upstream CTAN URLs for `tex.web`, `tangle.web`, and `weave.web`.

Keep canonical upstream files untouched. Local work should live in build scripts, change files, and documentation. If you add generated artifacts such as `tex.p`, compiler logs, or bootstrap binaries, keep them out of version control unless the change explicitly documents why they are needed.

## Build, Test, and Development Commands

Use the README as the source of truth for the current workflow.

- `cat sources` reviews the expected upstream inputs before fetching.
- `sha256sum tex.web tangle.web weave.web` verifies downloaded files against the checksums documented in `README.md`.
- `make` is the intended build entrypoint once the build script exists on your branch; it should drive the `tex.web -> tex.p -> fpc` pipeline.
- `git diff --check` catches trailing whitespace and malformed patches before opening a PR.

When experimenting, record the exact `fpc` version and any bootstrap `tangle` provenance in your notes or PR description.

## Coding Style & Naming Conventions

Prefer small, reviewable changes. Use concise Markdown and wrap prose sensibly for readability. For scripts, favor portable shell over environment-specific behavior unless a tool requires otherwise. Name new files descriptively by role, for example `bootstrap.mk`, `tex-fpc.ch`, or `docs/error-taxonomy.md`.

Do not edit canonical `tex.web`; encode repository-specific behavior in change files or helper scripts.

## Testing Guidelines

There is no committed automated test suite yet. Until one exists, treat reproducibility as the main test:

- verify upstream file hashes,
- run the documented build path,
- capture compiler diagnostics clearly.

If you add tests, place them in a dedicated `tests/` directory and name scripts after the behavior they verify, such as `tests/bootstrap-smoke.sh`.

## Commit & Pull Request Guidelines

Current history uses short, descriptive subjects such as `README.md for TeXactly`. Follow that pattern with clear, focused commit titles and keep unrelated changes split across commits.

Pull requests should explain:

- what changed,
- why it is needed for the bootstrap effort,
- which commands were run,
- what tool versions and diagnostics were observed.

Include log excerpts only when they help reviewers reproduce or understand a failure mode.
