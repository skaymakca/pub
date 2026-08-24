.PHONY: help dev build clean check-hugo

# Single source of truth for the Hugo version is the deploy workflow.
HUGO_PIN   := $(shell sed -n "s/.*HUGO_VERSION: '\(.*\)'.*/\1/p" .github/workflows/deploy.yml)
HUGO_LOCAL := $(shell hugo version 2>/dev/null | sed -n 's/^hugo v\([0-9][0-9.]*\).*/\1/p')

help: ## Show this help message
	@echo "Pub - Available make commands:"
	@echo ""
	@awk '/^##@/{printf "\n  \033[1m%s\033[0m\n",substr($$0,5)} /^[a-zA-Z_-]+:.*## /{t=$$0;sub(/:.*/, "",t);d=$$0;sub(/^[^#]*## /,"",d);printf "  \033[36m%-18s\033[0m %s\n",t,d}' $(MAKEFILE_LIST)
	@echo ""

##@ Development

dev: ## Start local dev server with live reload (opens browser)
	@sleep 2 && open http://localhost:1313/pub/ &
	hugo server --buildDrafts

build: check-hugo ## Production build into public/
	hugo --minify

##@ Cleanup

clean: ## Remove build artifacts
	rm -rf public/ resources/

##@ Checks

check-hugo: ## Fail if local Hugo differs from the version CI pins
	@if [ -z "$(HUGO_LOCAL)" ]; then \
		echo "hugo not found on PATH"; exit 1; \
	elif [ "$(HUGO_PIN)" = "$(HUGO_LOCAL)" ]; then \
		echo "hugo $(HUGO_LOCAL) matches the CI pin"; \
	else \
		echo "VERSION DRIFT: local hugo $(HUGO_LOCAL), CI pins $(HUGO_PIN)"; \
		echo "  what you build locally is not what deploys."; \
		echo "  fix: bump HUGO_VERSION in .github/workflows/deploy.yml,"; \
		echo "       or 'brew install hugo@$(HUGO_PIN)'"; \
		exit 1; \
	fi
