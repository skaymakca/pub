.PHONY: help dev build clean

help: ## Show this help message
	@echo "Pub - Available make commands:"
	@echo ""
	@awk '/^##@/{printf "\n  \033[1m%s\033[0m\n",substr($$0,5)} /^[a-zA-Z_-]+:.*## /{t=$$0;sub(/:.*/, "",t);d=$$0;sub(/^[^#]*## /,"",d);printf "  \033[36m%-18s\033[0m %s\n",t,d}' $(MAKEFILE_LIST)
	@echo ""

##@ Development

dev: ## Start local dev server with live reload (opens browser)
	@open http://localhost:1313/pub/ &
	hugo server --buildDrafts

build: ## Production build into public/
	hugo --minify

##@ Cleanup

clean: ## Remove build artifacts
	rm -rf public/ resources/
