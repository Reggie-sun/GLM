VENV_PYTHON := .venv/bin/python
PYTHON ?= $(shell if [ -x $(VENV_PYTHON) ]; then echo $(VENV_PYTHON); else command -v python3 2>/dev/null || command -v python 2>/dev/null; fi)

APP_DEBUG ?= false
ACCOUNT_ID ?= 1
TARGET_URL ?= https://bigmodel.cn/glm-coding
OUTPUT_DIR ?= data/captures
WATCH_SECONDS ?= 1800
REFRESH_INTERVAL ?= 2
SETTLE_SECONDS ?= 5
PURCHASE_TIMEOUT_MS ?= 20000
POLL_INTERVAL ?= 30
WAIT_TIMEOUT_SECONDS ?= 0
TARGET_TIME ?= 10:00
TIMEZONE ?= Asia/Hong_Kong
PREWARM_SECONDS ?= 600
RUN_SECONDS ?= 1200
WAIT_LOGIN_SECONDS ?= 0
KEEP_OPEN_SECONDS ?= 0
SCREENSHOT_PATH ?= data/screenshots/payment_page.png
HEADED ?= 1
WAIT_FOR_STOCK ?= 0
SAME_ORIGIN_PROBE ?= 0
PROBE_ENDPOINTS ?=
EXTRA_ARGS ?=

HEADED_FLAG :=
WAIT_FOR_STOCK_FLAGS :=
SAME_ORIGIN_PROBE_FLAGS :=

ifneq ($(strip $(HEADED)),0)
HEADED_FLAG += --headed
endif

ifneq ($(strip $(WAIT_FOR_STOCK)),0)
WAIT_FOR_STOCK_FLAGS += --wait-for-stock --poll-interval $(POLL_INTERVAL) --timeout-seconds $(WAIT_TIMEOUT_SECONDS)
endif

ifneq ($(strip $(SAME_ORIGIN_PROBE)),0)
SAME_ORIGIN_PROBE_FLAGS += --same-origin-probe
endif

ifneq ($(strip $(PROBE_ENDPOINTS)),)
SAME_ORIGIN_PROBE_FLAGS += $(foreach endpoint,$(PROBE_ENDPOINTS),--probe-endpoint $(endpoint))
endif

.DEFAULT_GOAL := help

.PHONY: help verify-purchase auto-buy prewarm-buy

help: ## Show available Make targets and overridable variables.
	@echo "Usage: make <target> [VAR=value]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_.-]+:.*## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Common variables:"
	@echo "  ACCOUNT_ID=1 TARGET_URL=$(TARGET_URL)"
	@echo "  WATCH_SECONDS=$(WATCH_SECONDS) REFRESH_INTERVAL=$(REFRESH_INTERVAL)"
	@echo "  HEADED=$(HEADED) WAIT_FOR_STOCK=$(WAIT_FOR_STOCK) SAME_ORIGIN_PROBE=$(SAME_ORIGIN_PROBE)"
	@echo "  TARGET_TIME=$(TARGET_TIME) TIMEZONE=$(TIMEZONE) PREWARM_SECONDS=$(PREWARM_SECONDS)"

verify-purchase: ## Run the local purchase setup verification script.
	DEBUG=$(APP_DEBUG) $(PYTHON) scripts/verify_purchase_setup.py

auto-buy: ## Watch stock and start one controlled purchase attempt when a package button becomes actionable.
	DEBUG=$(APP_DEBUG) $(PYTHON) scripts/capture_purchase_flow.py \
		--account-id $(ACCOUNT_ID) \
		--target-url $(TARGET_URL) \
		--output-dir $(OUTPUT_DIR) \
		--watch-seconds $(WATCH_SECONDS) \
		--refresh-interval $(REFRESH_INTERVAL) \
		--settle-seconds $(SETTLE_SECONDS) \
		--purchase-timeout-ms $(PURCHASE_TIMEOUT_MS) \
		--stop-on-actionable \
		--attempt-purchase-on-actionable \
		$(WAIT_FOR_STOCK_FLAGS) \
		$(HEADED_FLAG) \
		$(SAME_ORIGIN_PROBE_FLAGS) \
		$(EXTRA_ARGS)

prewarm-buy: ## Prewarm before TARGET_TIME and arm a real purchase attempt after the target window starts.
	DEBUG=$(APP_DEBUG) $(PYTHON) scripts/prewarm_purchase.py \
		--account-id $(ACCOUNT_ID) \
		--target-url $(TARGET_URL) \
		--target-time $(TARGET_TIME) \
		--timezone $(TIMEZONE) \
		--prewarm-seconds $(PREWARM_SECONDS) \
		--run-seconds $(RUN_SECONDS) \
		--refresh-interval $(REFRESH_INTERVAL) \
		--purchase-timeout-ms $(PURCHASE_TIMEOUT_MS) \
		--wait-login-seconds $(WAIT_LOGIN_SECONDS) \
		--keep-open-seconds $(KEEP_OPEN_SECONDS) \
		--screenshot-path $(SCREENSHOT_PATH) \
		--execute \
		$(HEADED_FLAG) \
		$(EXTRA_ARGS)
