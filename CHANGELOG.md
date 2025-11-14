# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Fix 2 failing test edge cases
- Increase test coverage to 85%
- CLI integration tests
- Regime detection implementation
- HRP weighting option
- Monitoring dashboard

---

## [0.1.0] - 2025-11-11

### Added
- **Core Strategy Implementation**
  - Momentum scoring with ATR normalization
  - EMA trend filtering (EMA20 > EMA50)
  - Correlation-capped asset selection (≤0.7)
  - Inverse-volatility weighting with caps
  - Fractional position sizing

- **Research Infrastructure**
  - Backtesting engine with strict no look-ahead
  - Walk-forward optimization (rolling 3yr train / 3mo OOS)
  - Permutation testing (IMCPT-lite with joint permutations)
  - Performance metrics (CAGR, Sharpe, Calmar, MaxDD, PF, Turnover)
  - Visualization (equity curve, drawdown, monthly heatmap)

- **IBKR Integration**
  - Connection via ib_insync
  - Historical data fetching (delayed mode, no subscriptions)
  - Fractional order construction
  - Dry-run, paper, and live execution modes
  - Parquet caching for historical data

- **Risk Management & Compliance**
  - Settlement guard (prevents unsettled cash trading)
  - Position limits (max 50% per asset)
  - Order throttling (max 5 orders/day)
  - Rebalance limiter (once per day)
  - PDT counter (defensive)
  - Comprehensive audit logging (JSONL format)

- **Testing & Quality**
  - 208 unit tests across 38 test files
  - 71% code coverage
  - Ruff linting
  - Mypy type checking
  - pytest-cov for coverage tracking
  - Mock-based tests for IBKR integration

- **Infrastructure**
  - Docker containerization
  - Docker Compose orchestration
  - Poetry dependency management
  - Makefile for convenience commands
  - YAML-based configuration with local overrides
  - Environment variable support

- **Documentation**
  - Project README with quick start guide
  - Technical specification (docs/README.md)
  - Project status dashboard (PROJECT_STATUS.md)
  - TODO list and roadmap (TODO.md)
  - Memory and lessons learned (docs/context/memory.md)
  - Inline code documentation and type hints

- **CLI Commands**
  - `bot connect` - Verify IBKR connection
  - `bot fetch` - Fetch historical data
  - `bot backtest` - Run backtest
  - `bot walkforward` - Run walk-forward optimization
  - `bot permute` - Run permutation test
  - `bot weights` - Calculate target weights for a date
  - `bot trade` - Execute rebalance (dry-run/paper/live)

- **Default Universe**
  - SPY (US large-cap)
  - QQQ (tech-heavy)
  - VTI (broad US market)
  - TLT (long-term treasuries)
  - IEF (intermediate treasuries)
  - GLD (gold)
  - XLE (energy)
  - BND (aggregate bonds)
  - BITO (bitcoin exposure)

### Technical Details
- **Python**: 3.11
- **Key Dependencies**: 
  - ib_insync 0.9.86
  - pandas 2.1.0
  - numpy 1.26.0
  - pyarrow 14.0.0
  - matplotlib 3.8.0
  - click 8.1.7
  - pydantic 2.5.0
  - pytest 7.4.3

### Known Issues
- 2 test edge cases failing (date range filtering, live mode mock)
- CLI module not covered by unit tests (integration tests planned)
- Broker adapter stubs (Alpaca/Tiingo) at 0% coverage
- Some error paths in IBKR modules not fully tested

### Configuration Defaults
- **Rebalance**: Daily at 15:55 ET
- **Selection**: Top 2 assets, correlation cap 0.7, 90-day rolling window
- **Weighting**: Inverse-volatility, 20-day window, 50% max per asset, 5% cash buffer
- **Costs**: 0.0035/share commission, 1bp slippage
- **Account**: Paper (DUK200445), ~$25k starting capital

---

## [0.0.1] - 2025-11-10

### Initial Setup
- Project structure created
- Basic module scaffolding
- Development environment configured
- Git repository initialized

---

## Version History Summary

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| 0.1.0 | 2025-11-11 | ✅ Complete | Core system, ready for paper trading |
| 0.0.1 | 2025-11-10 | ✅ Complete | Initial setup |

---

## Future Versions (Planned)

### [0.2.0] - TBD (After Paper Trading)
- CLI integration tests
- Increased coverage to 85%+
- Fixed test edge cases
- Paper trading results documented
- Performance benchmarks established

### [0.3.0] - TBD
- Regime detection (SPX 200DMA, VIX threshold)
- HRP weighting option
- Enhanced monitoring and alerting
- Dashboard implementation

### [1.0.0] - TBD (Production Release)
- Paper trading validation complete (3+ months)
- Parameters frozen based on walk-forward results
- All tests passing at 85%+ coverage
- Documentation complete and reviewed
- Ready for live trading

---

## Release Process

1. **Development**: Feature branches, PR reviews
2. **Testing**: All tests pass, coverage maintained
3. **Documentation**: Update CHANGELOG, README, docs
4. **Version Bump**: Update pyproject.toml
5. **Tag**: Git tag with version number
6. **Deploy**: Docker image build and tag
7. **Validate**: Run full test suite in deployment environment

---

## Deprecation Policy

- **Major version** (X.0.0): Breaking changes, API redesign
- **Minor version** (0.X.0): New features, backward compatible
- **Patch version** (0.0.X): Bug fixes, no API changes

**Notice Period**: 
- Breaking changes announced 1 month in advance
- Deprecated features supported for 2 minor versions minimum

---

## Links
- [Project README](README.md)
- [Technical Specification](docs/README.md)
- [Project Status](PROJECT_STATUS.md)
- [TODO List](TODO.md)
- [Contributing Guide](CONTRIBUTING.md) *(to be created)*

---

**Maintained By**: Development Team  
**Last Updated**: 2025-11-11  
**Next Release**: TBD (pending paper trading validation)





