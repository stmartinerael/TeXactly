# TODO

The live source of truth for action items, comments, prompt sketches, and known
errors is now `project-tracker.json`, viewed through `make viewer`.

Treat the list below as a readable snapshot of that tracker, not the canonical
place to edit project state.

## Immediate Next Steps

- [ ] Commit the new bootstrap scaffolding:
  - `Makefile`
  - `checksums.sha256`
  - `taxonomy-rules.tsv`
  - `scripts/generate_taxonomy.py`
  - updated `README.md`
- [ ] Re-run the baseline probe from a clean checkout and confirm the documented flow still works:
  - `make fetch`
  - `make verify`
  - `make tangle`
  - `make all`
- [ ] Save a canonical first-pass `fpc.log` and `error-taxonomy.md` snapshot outside git for comparison against future changes.

## FPC Error Investigation

- [ ] Triage the current blocking diagnostics in order of impact:
  - typed-file `readln`/`writeln` usage
  - missing `others`
  - constant-expression failures
  - cross-procedure `goto`
  - fatal syntax error near line 403 of `tex.p`
- [ ] Decide which failures should be handled by:
  - a TeX change file
  - an alternate compiler flag or mode
  - a documented “not supported by FPC” finding
- [ ] Record each investigated failure with:
  - the exact `tex.p` location
  - the generated Pascal snippet
  - the suspected WEB construct behind it
  - the chosen resolution or conclusion

## Taxonomy Improvements

- [ ] Expand `taxonomy-rules.tsv` as new diagnostics appear.
- [ ] Group repeated messages more aggressively where only numeric ranges differ.
- [ ] Add a short “How to read the taxonomy” section to the generated report or README.
- [ ] Capture whether a category is:
  - syntax-only
  - semantic/type-system related
  - runtime/I-O related
  - likely fixable via change file

## Build and Repo Hygiene

- [ ] Add a `make probe` or `make report` target if we want a clearer one-command diagnostic workflow than `make all`.
- [ ] Consider writing `fpc` metadata and host info to a separate machine-readable file.
- [ ] Add a small shell test that checks `make verify`, `make tangle`, and taxonomy generation on systems with the required tools.
- [ ] Decide whether fetched WEB sources should remain root-level long-term or move into a dedicated untracked directory later.

## Documentation

- [ ] Add a contributor note describing the current known FPC failures.
- [ ] Document the rule that canonical `tex.web` stays untouched and all adaptation must live in change files or helper scripts.
- [ ] Add a roadmap section to `README.md` so the repo clearly communicates the next milestone after taxonomy.
