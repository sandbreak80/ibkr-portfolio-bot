# Project Memory

Use this file to capture commands, configuration nuances, and operational lessons that should persist across runs.

## Project Status (Last Updated: 2025-11-11)

### Current State
- **Phase**: Paper Trading Validation
- **Test Status**: 206/208 passing (99% pass rate)
- **Coverage**: 71% overall
- **Build**: All pipelines passing (build, lint, typecheck)

### Test Failures (2)
1. `test_run_backtest_date_range_filtering` - Edge case in date range filtering logic
2. `test_execute_rebalance_live_mode` - Live mode execution edge case

### Architecture Overview
- **Strategy**: Long-only momentum rotation with correlation cap (≤0.7)
- **Universe**: 9 liquid ETFs (SPY, QQQ, VTI, TLT, IEF, GLD, XLE, BND, BITO)
- **Rebalance**: Daily at 15:55 ET, top 2 assets selected
- **Weighting**: Inverse volatility with 50% max per asset, 5% cash buffer
- **Execution**: Fractional orders via IBKR (ib_insync)

### Key Design Decisions

#### No Look-Ahead Prevention
- All positions lagged by +1 bar in backtest
- Signals calculated on bar t, position taken on bar t+1
- Enforced by tests (`test_no_look_ahead`)

#### Correlation Cap Rationale
- Prevents over-concentration in similar assets (e.g., SPY vs VTI at 0.95 corr)
- Uses 90-day rolling return correlations
- Greedy selection algorithm: checks correlation with all already-selected assets
- In crisis, correlations → 1, system naturally reduces positions and holds cash

#### Cash Account Discipline
- Long-only, no leverage, no shorting
- Settlement guard prevents trading unsettled funds
- PDT counter (defensive, though cash accounts exempt)
- Max 5 orders/day hard limit

#### Determinism & Reproducibility
- All random operations seeded (backtest.seed: 42)
- Walk-forward uses same seed for reproducible optimization
- Permutation tests use explicit seeds
- Audit logs capture full state for each rebalance

### Module Coverage Summary
- **High coverage (90%+)**: types, risk, metrics, indicators, scoring, weighting
- **Medium coverage (70-89%)**: clock, config, backtest, signals, walkforward, correlation
- **Needs improvement (<70%)**: ibkr_client, ibkr_exec, permutation
- **Not tested**: CLI (0%), adapter stubs (0%)

### Known Limitations & Trade-offs

#### Data & Timing
- Uses IBKR delayed data (no subscription fees) - acceptable for daily strategy
- Small timestamp misalignments possible vs exchange official times
- Rebalance at 15:55 ET (5 min before close) - balances execution risk vs end-of-day prices

#### Correlation Management
- Correlation cap is point-in-time; correlations shift by regime
- During crises, all assets correlate → fewer positions → more cash (defensive)
- No explicit regime detection (future enhancement opportunity)

#### Costs & Slippage
- Fixed cost model (0.0035/share commission + 1bp slippage)
- Real slippage varies by market conditions
- No market impact model (assumes small size)

#### Tax Considerations
- No tax modeling
- Strategy rebalances daily → potentially high turnover
- Better suited for tax-advantaged accounts (IRA, 401k)

### Operational Commands

```bash
# Full validation cycle
make build lint typecheck test

# Research workflow
docker compose run --rm app poetry run bot fetch
docker compose run --rm app poetry run bot backtest
docker compose run --rm app poetry run bot walkforward
docker compose run --rm app poetry run bot permute --runs 200

# Trading workflow (paper)
docker compose run --rm app poetry run bot weights --asof $(date +%Y-%m-%d)
docker compose run --rm app poetry run bot trade --dry-run --paper

# Cleanup
make clean  # Removes volumes, artifacts, cached data
```

### Configuration Hierarchy
1. `config/config.yaml` - Base defaults (committed)
2. `config/config.local.yaml` - Local overrides (gitignored)
3. Environment variables (`.env`) - Secrets & host-specific

### Development Workflow

#### Adding Tests
- Unit tests in `tests/test_*.py`
- Integration tests in `tests/test_integration.py`
- Coverage target: 85% unit, 70% integration
- Run: `make test`

#### Debugging
- Logs: `reports/logs/*.jsonl` (audit trail)
- Artifacts: `artifacts/*.log` (build/test logs)
- Plots: `reports/*.png` (equity, drawdown, heatmap)
- Metrics: `reports/metrics.json`

#### Pre-commit Checklist
1. `make lint` (ruff)
2. `make typecheck` (mypy)
3. `make test` (pytest)
4. Review coverage report: `htmlcov/index.html`

### Future Enhancements (Parking Lot)

#### High Priority
- [ ] Fix 2 failing tests
- [ ] Increase CLI coverage (integration tests)
- [ ] Add regime detection (SPX 200DMA, VIX threshold)
- [ ] Implement HRP weighting as alternative to inv-vol

#### Medium Priority
- [ ] Real-time monitoring dashboard
- [ ] Slack/email alerts for rebalance events
- [ ] Enhanced error recovery (retry logic)
- [ ] Multiple universe support (ETF, stocks, sectors)

#### Low Priority
- [ ] Alpaca/Tiingo adapter completion (currently stubs)
- [ ] Intraday rebalancing support (hourly bars)
- [ ] Machine learning scoring alternative
- [ ] Multi-account support

### Lessons Learned

#### What Works Well
- Docker isolation prevents "works on my machine" issues
- Parquet caching significantly speeds up research iteration
- Strict no-look-ahead testing caught several bugs early
- Walk-forward optimization revealed parameter sensitivity
- Permutation testing confirmed strategy has real edge (p < 0.05)

#### Gotchas & Pitfalls
- IBKR historical data pacing: use exponential backoff, chunk requests
- pandas DatetimeIndex timezone handling: always work in UTC, convert to ET only for display
- Correlation matrices can be ill-conditioned: add epsilon for numerical stability
- ib_insync async context: requires proper await/disconnect handling
- Docker volume permissions: ensure writable reports/artifacts directories

#### Best Practices Established
- Always test with synthetic data first (known ground truth)
- Use fixtures for common test data patterns
- Parametrize tests for edge cases (empty data, single asset, flat prices)
- Log state transitions (selection, weighting, order generation)
- Separate research code (backtest) from live code (execution) - but keep logic identical

### References & Resources
- [IB API Documentation](https://www.interactivebrokers.com/en/index.php?f=5041)
- [ib_insync Examples](https://ib-insync.readthedocs.io/)
- [Walk-Forward Analysis](https://en.wikipedia.org/wiki/Walk_forward_optimization)
- [IMCPT Paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3206042) - Permutation testing methodology

---

**Last maintenance check**: 2025-11-11
**Next review date**: After paper trading period (3 months minimum)