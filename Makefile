SHELL := /bin/sh

CURL ?= curl
SHA256SUM ?= sha256sum
TANGLE ?= tangle
FPC ?= fpc
PYTHON ?= python3

SOURCE_MANIFEST := sources
CHECKSUMS := checksums.sha256
TAXONOMY_RULES := taxonomy-rules.tsv
TAXONOMY_SCRIPT := scripts/generate_taxonomy.py

FETCHED_SOURCES := tex.web tangle.web weave.web
TANGLE_OUTPUTS := tex.p tex.pool
COMPILE_LOG := fpc.log
TAXONOMY_REPORT := error-taxonomy.md
FPC_OUTPUTS := tex tex.o

.PHONY: all fetch verify tangle compile taxonomy viewer clean \
	check-fetch-tools check-verify-tools check-tangle-tools \
	check-compile-tools check-taxonomy-tools

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

clean:
	@rm -f $(FETCHED_SOURCES) $(TANGLE_OUTPUTS) $(COMPILE_LOG) $(TAXONOMY_REPORT) $(FPC_OUTPUTS)

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
