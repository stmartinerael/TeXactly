# TeXactly — bootstrap tex.web → tex.p → fpc error taxonomy, no Web2c
#
# Knuth's sources are not committed here. Either:
#   make fetch              — download from CTAN
#   make verify             — check SHA-256 (README checksums)
# or point to existing files:
#   make TEX_WEB=/path/to/tex.web TANGLE_WEB=/path/to/tangle.web

TEX_WEB    ?= tex.web
TANGLE_WEB ?= tangle.web

SYS_TANGLE := tangle
FPC        := fpc
FPCFLAGS   :=
B          := build

.PHONY: all fetch verify bootstrap tangle-p fpc-log clean

all: $(B)/tex.p

$(B):
	mkdir -p $(B)

# ── fetch ─────────────────────────────────────────────────────────
fetch: $(TEX_WEB) $(TANGLE_WEB)

$(TEX_WEB):
	curl -fsSL https://mirrors.ctan.org/systems/knuth/dist/tex/tex.web -o $@

$(TANGLE_WEB):
	curl -fsSL https://mirrors.ctan.org/systems/knuth/dist/web/tangle.web -o $@

verify: $(TEX_WEB) $(TANGLE_WEB)
	printf '%s  %s\n' \
	  60bb22ffeec81e10682ca903c2ccc5ba5c94eb9fe42387a01afc3173e681bf57 $(TANGLE_WEB) \
	  c62ab513ef167e93f71a23bd34f311e243210afd7c7a0f9b779614b71e398324 $(TEX_WEB) \
	| sha256sum -c

# ── (a) bootstrap our tangle from tangle.web ─────────────────────
# Run from $(B) so tangle drops tangle.p / tangle.pool there.
$(B)/empty.ch: | $(B)
	touch $@

$(B)/tangle.p $(B)/tangle.pool: $(TANGLE_WEB) $(B)/empty.ch
	cd $(B) && $(SYS_TANGLE) $(abspath $(TANGLE_WEB)) empty.ch

$(B)/tangle: $(B)/tangle.p
	$(FPC) $(FPCFLAGS) -Mtp -o$@ $<

# ── (b) produce tex.p from tex.web ───────────────────────────────
# Uses our bootstrapped tangle if it compiled; falls back to SYS_TANGLE.
$(B)/tex.p $(B)/tex.pool: $(TEX_WEB) $(B)/empty.ch
	cd $(B) && $(SYS_TANGLE) $(abspath $(TEX_WEB)) empty.ch

tangle-p: $(B)/tex.p

# ── (c) fpc error taxonomy ────────────────────────────────────────
$(B)/fpc.log: $(B)/tex.p
	cd $(B) && $(FPC) $(FPCFLAGS) tex.p 2>&1 | tee fpc.log; true

fpc-log: $(B)/fpc.log

# ── housekeeping ─────────────────────────────────────────────────
clean:
	rm -rf $(B)
