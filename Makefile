# =============================================================================
# Nuxel — Top-level Makefile (briq-ci1 build wiring)
#
# Wires the build so that the canonical single-source assets are copied at
# build time (tools/dedupe-assets.sh) and every artifact lands under
# build/output/ (OUTPUT_DIR in images/build.sh already points there).
#
# The heavy lifting stays in the committed scripts:
#   - images/build.sh   kernel -> initramfs -> rootfs -> boot images -> package
#   - tools/dedupe-assets.sh   single-source PWA asset population
#   - ci/validate-build.sh     real-artifact assertions (PASS/FAIL + exit code)
#
# Targets:
#   make            = make build
#   make build      = dedupe assets, then run images/build.sh (artifacts under
#                     build/output)
#   make assets     = populate per-app asset copies from the canonical assets/
#   make validate   = run ci/validate-build.sh against build/output
#   make ci         = full CI gate: dedupe(populate) + validate
# =============================================================================

SHELL := /bin/bash

# Explicit device key for the multi-device layout (device-selected dirs).
# Defaults to mustang so make build/validate/ci keep the historical mustang
# behaviour; scripts resolve per-device paths via the shared selector
# (tools/nuxel-device-select.sh).
NUXEL_DEVICE ?= mustang
export NUXEL_DEVICE

NUXEL_ROOT := $(CURDIR)
OUTPUT_DIR := $(NUXEL_ROOT)/build/output
DEDUPE     := $(NUXEL_ROOT)/tools/dedupe-assets.sh
BUILD_SCRIPT := $(NUXEL_ROOT)/images/build.sh
VALIDATE   := $(NUXEL_ROOT)/ci/validate-build.sh
VERIFY_PWA := $(NUXEL_ROOT)/tools/verify-pwa-assets.sh

.PHONY: all build assets validate ci clean clean-output

all: build

# Dedupe (single-source) asset population runs before any build step.
build: assets
	@echo ""
	@echo "==> Nuxel build: images/build.sh (artifacts -> build/output)"
	@mkdir -p "$(OUTPUT_DIR)"
	@bash "$(BUILD_SCRIPT)"
	@echo "==> Ensuring canonical artifacts are present under build/output/"
	@if [ -d "$(NUXEL_ROOT)/build/boot-artifact" ]; then \
	  for f in boot.img initramfs.cpio.gz; do \
	    if [ -f "$(NUXEL_ROOT)/build/boot-artifact/$$f" ] && [ ! -f "$(OUTPUT_DIR)/$$f" ]; then \
	      cp -f "$(NUXEL_ROOT)/build/boot-artifact/$$f" "$(OUTPUT_DIR)/$$f" && \
	      echo "   consolidated $(OUTPUT_DIR)/$$f"; \
	    fi; \
	  done; \
	fi
	@echo "==> Done. Artifacts under: $(OUTPUT_DIR)"

assets:
	@echo "==> Populating single-source PWA assets (tools/dedupe-assets.sh)"
	@if [ -x "$(DEDUPE)" ]; then bash "$(DEDUPE)"; \
	else echo "[warn] $(DEDUPE) not found — skipping asset de-dupe"; fi

validate:
	@echo "==> Single-source PWA asset invariant (tools/verify-pwa-assets.sh --quiet)"
	@if [ -x "$(VERIFY_PWA)" ]; then bash "$(VERIFY_PWA)" --quiet; 	else echo "[warn] $(VERIFY_PWA) not found — skipping single-source asset verify"; fi
	@echo "==> Nuxel build validation (ci/validate-build.sh)"
	@bash "$(VALIDATE)"

# Full CI gate: populate assets, run the top-level build, then validate the
# real artifacts. ci/validate-build.sh exits non-zero when real state is broken.
ci: build
	@echo "==> CI gate: single-source PWA asset invariant (tools/verify-pwa-assets.sh --quiet)"
	@if [ -x "$(VERIFY_PWA)" ]; then bash "$(VERIFY_PWA)" --quiet; 	else echo "[warn] $(VERIFY_PWA) not found — skipping single-source asset verify"; fi
	@echo "==> CI gate: validating real build artifacts"
	@bash "$(VALIDATE)"

clean-output:
	@rm -rf "$(OUTPUT_DIR)"
	@echo "Removed $(OUTPUT_DIR)"

clean: clean-output
	@echo "Cleaned build outputs."
