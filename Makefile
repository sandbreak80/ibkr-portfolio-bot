.PHONY: build lint typecheck test fetch backtest wf permute clean help

# Build Docker image
build:
	docker compose build

# Lint code
lint:
	docker compose run --rm app poetry run ruff check src/ tests/

# Type check
typecheck:
	docker compose run --rm app poetry run mypy src/

# Run tests (with pre-flight cleanup to prevent duplicates)
test:
	@echo "🧹 Cleaning up any stale test containers..."
	@docker ps -q --filter "name=stock_portfolio-app-run" 2>/dev/null | xargs -r docker kill 2>/dev/null || true
	@docker ps -a -q --filter "name=stock_portfolio-app-run" --filter "status=exited" 2>/dev/null | xargs -r docker rm 2>/dev/null || true
	@echo "✓ Cleanup complete, starting tests..."
	docker compose run --rm app poetry run pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html --cov-report=json

# Fetch historical data
fetch:
	docker compose run --rm app poetry run bot fetch

# Run backtest
backtest:
	docker compose run --rm app poetry run bot backtest

# Walk-forward test
wf:
	docker compose run --rm app poetry run bot walkforward

# Permutation test
permute:
	docker compose run --rm app poetry run bot permute

# Clean artifacts
clean:
	docker compose down -v
	rm -rf artifacts/* reports/* data/parquet/*

# Help
help:
	@echo "Available targets:"
	@echo "  build      - Build Docker image"
	@echo "  lint       - Run ruff linter"
	@echo "  typecheck  - Run mypy type checker"
	@echo "  test       - Run pytest with coverage"
	@echo "  fetch      - Fetch historical data"
	@echo "  backtest   - Run backtest"
	@echo "  wf         - Run walk-forward test"
	@echo "  permute    - Run permutation test"
	@echo "  clean      - Clean volumes and artifacts"
