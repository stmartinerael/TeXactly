SHELL := /bin/sh

CURL ?= curl
SHA256SUM ?= sha256sum
TANGLE ?= tangle
FPC ?= fpc
PYTHON ?= python3

WEBMAN_URL := https://mirrors.ctan.org/systems/knuth/dist/web/webman.tex
WEBMAN_TEX := webman.tex
WEBMAN_MD := webman.md
CONVERT_SCRIPT := scripts/tex_to_md.py

SOURCE_MANIFEST := sources
CHECKSUMS := checksums.sha256
TAXONOMY_RULES := taxonomy-rules.tsv
TAXONOMY_SCRIPT := scripts/generate_taxonomy.py

FETCHED_SOURCES := tex.web tangle.web weave.web
TANGLE_OUTPUTS := tex.p tex.pool
COMPILE_LOG := fpc.log
TAXONOMY_REPORT := error-taxonomy.md
FPC_OUTPUTS := tex tex.o

.PHONY: all help fetch verify tangle compile taxonomy viewer doc clean \
	check-fetch-tools check-verify-tools check-tangle-tools \
	check-compile-tools check-taxonomy-tools

help:
	@echo 'Usage: make <target>'
	@echo ''
	@echo 'Targets:'
	@echo '  all       Run fetch, verify, tangle, compile, taxonomy'
	@echo '  fetch     Download sources listed in $(SOURCE_MANIFEST)'
	@echo '  verify    Check fetched sources against $(CHECKSUMS)'
	@echo '  tangle    Run $(TANGLE) on tex.web to produce $(TANGLE_OUTPUTS)'
	@echo '  compile   Compile tex.p with $(FPC); log to $(COMPILE_LOG)'
	@echo '  taxonomy  Generate $(TAXONOMY_REPORT) from $(COMPILE_LOG)'
	@echo '  viewer    Run the progress viewer script'
	@echo '  doc       Download $(WEBMAN_TEX) and convert to $(WEBMAN_MD)'
	@echo '  clean     Remove fetched, tangled, compiled, and report artifacts'
	@echo '  help      Show this message'

all:
	@$(MAKE) fetch
	@$(MAKE) verify
	@$(MAKE) tangle
	@rc=0; \
	$(MAKE) compile || rc=$$?; \
	$(MAKE) taxonomy; \
	exit $$rc

fetch: check-fetch-tools $(SOURCE_MANIFEST)
	@while IFS= read -r url; do \
		case "$$url" in \
			''|\#*) continue ;; \
		esac; \
		file=$${url##*/}; \
		if [ -f "$$file" ]; then \
			printf 'Using existing %s\n' "$$file"; \
		else \
			printf 'Fetching %s\n' "$$file"; \
			$(CURL) -L --fail --silent --show-error -o "$$file" "$$url"; \
		fi; \
	done < $(SOURCE_MANIFEST)

verify: check-verify-tools $(CHECKSUMS) $(FETCHED_SOURCES)
	@$(SHA256SUM) --check $(CHECKSUMS)

tangle: check-tangle-tools tex.web
	@rm -f $(TANGLE_OUTPUTS)
	@$(TANGLE) tex.web
	@[ -s tex.p ] || { echo "tangle did not produce tex.p"; exit 1; }

compile: check-compile-tools tex.p
	@rm -f $(COMPILE_LOG)
	@rc=0; \
	{ \
		printf '# Generated: %s\n' "$$(date --iso-8601=seconds)"; \
		printf '# FPC version: %s\n' "$$($(FPC) -iV)"; \
		printf '# Command: %s tex.p\n' "$(FPC)"; \
		$(FPC) tex.p; \
	} > $(COMPILE_LOG) 2>&1 || rc=$$?; \
	printf '# Exit code: %s\n' "$$rc" >> $(COMPILE_LOG); \
	exit $$rc

taxonomy: check-taxonomy-tools $(COMPILE_LOG) $(TAXONOMY_RULES) $(TAXONOMY_SCRIPT)
	@$(PYTHON) $(TAXONOMY_SCRIPT) \
		--log $(COMPILE_LOG) \
		--rules $(TAXONOMY_RULES) \
		--output $(TAXONOMY_REPORT)

viewer: check-taxonomy-tools project-tracker.json scripts/progress_viewer.py
	@$(PYTHON) scripts/progress_viewer.py

doc: $(WEBMAN_MD)

$(WEBMAN_TEX):
	@printf 'Fetching %s\n' "$@"
	@$(CURL) -L --fail --silent --show-error -o "$@" $(WEBMAN_URL)

$(WEBMAN_MD): $(WEBMAN_TEX) $(CONVERT_SCRIPT)
	@printf 'Converting %s to %s\n' "$<" "$@"
	@$(PYTHON) $(CONVERT_SCRIPT) $< $@

clean:
	@rm -f $(FETCHED_SOURCES) $(TANGLE_OUTPUTS) $(COMPILE_LOG) $(TAXONOMY_REPORT) $(FPC_OUTPUTS) $(WEBMAN_TEX) $(WEBMAN_MD)

check-fetch-tools:
	@command -v $(CURL) >/dev/null 2>&1 || { echo "Missing required tool: $(CURL)"; exit 1; }

check-verify-tools:
	@command -v $(SHA256SUM) >/dev/null 2>&1 || { echo "Missing required tool: $(SHA256SUM)"; exit 1; }

check-tangle-tools:
	@command -v $(TANGLE) >/dev/null 2>&1 || { echo "Missing required tool: $(TANGLE)"; exit 1; }

check-compile-tools:
	@command -v $(FPC) >/dev/null 2>&1 || { echo "Missing required tool: $(FPC)"; exit 1; }

check-taxonomy-tools:
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "Missing required tool: $(PYTHON)"; exit 1; }
