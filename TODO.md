# TODO List

**Last Updated**: 2025-11-11

---

## 🔴 Critical (Before Live Trading)

- [ ] **Run 2-3 month paper trading validation**
  - Start dry-run mode first
  - Monitor fills, slippage, API stability
  - Compare paper vs backtest performance
  - Status: Not started
  - ETA: 3 months

- [ ] **Complete walk-forward optimization**
  - Run on full historical dataset
  - Select optimal parameters
  - Document parameter choices and rationale
  - Freeze configuration
  - Status: Code ready, needs execution
  - ETA: 1 week

- [ ] **Run permutation test validation**
  - Execute with 200+ permutations
  - Confirm p-value < 0.05 (strategy significance)
  - Document results
  - Status: Code ready, needs execution
  - ETA: 1 day

---

## 🟡 High Priority (Improves Quality)

### Testing
- [ ] **Fix failing test: `test_run_backtest_date_range_filtering`**
  - Location: `tests/test_backtest_expanded2.py`
  - Issue: Date range filtering edge case
  - Status: Identified, needs fix
  - ETA: 2 hours

- [ ] **Fix failing test: `test_execute_rebalance_live_mode`**
  - Location: `tests/test_execution_expanded2.py`
  - Issue: Live mode mock execution
  - Status: Identified, needs fix
  - ETA: 2 hours

- [ ] **Increase test coverage to 85%**
  - Current: 71%
  - Focus on: ibkr_client (76%), ibkr_exec (71%), correlation (67%), permutation (66%)
  - Status: Ongoing
  - ETA: 1 week

### Documentation
- [x] **Create project README.md**
  - Quick start guide
  - Architecture overview
  - Status: ✅ Complete

- [x] **Update docs/context/memory.md**
  - Current status
  - Design decisions
  - Lessons learned
  - Status: ✅ Complete

- [x] **Create PROJECT_STATUS.md**
  - Build health dashboard
  - Test coverage summary
  - Status: ✅ Complete

- [ ] **Create CHANGELOG.md**
  - Track version history
  - Document major changes
  - Status: Not started
  - ETA: 1 hour

---

## 🟢 Medium Priority (Nice to Have)

### Features
- [ ] **Implement regime detection**
  - SPX 200-day moving average filter
  - VIX threshold check
  - Adjust position sizing in high-volatility regimes
  - Status: Design phase
  - ETA: 1 week

- [ ] **Add HRP (Hierarchical Risk Parity) weighting**
  - Alternative to inverse-volatility
  - Better diversification across asset classes
  - Make configurable (inv_vol vs HRP)
  - Status: Research phase
  - ETA: 2 weeks

- [ ] **CLI integration tests**
  - Test connect command
  - Test fetch workflow
  - Test backtest command
  - Test trade dry-run
  - Status: Not started
  - ETA: 1 week

- [ ] **Enhanced error recovery**
  - Retry logic for transient errors
  - Exponential backoff for API rate limits
  - Graceful degradation
  - Status: Not started
  - ETA: 3 days

### Monitoring & Alerting
- [ ] **Set up monitoring dashboard**
  - Real-time performance metrics
  - Position tracking
  - Alert system
  - Status: Not started
  - ETA: 1 week

- [ ] **Implement Slack/email alerts**
  - Rebalance notifications
  - Error alerts
  - Daily performance summary
  - Status: Not started
  - ETA: 2 days

- [ ] **Add health check endpoint**
  - System status
  - Last rebalance time
  - Account summary
  - Status: Not started
  - ETA: 1 day

---

## 🔵 Low Priority (Future Enhancements)

### Data Sources
- [ ] **Complete Alpaca adapter**
  - Historical data fallback
  - Currently stub implementation
  - Status: Not started
  - ETA: 3 days

- [ ] **Complete Tiingo adapter**
  - Historical data fallback
  - Currently stub implementation
  - Status: Not started
  - ETA: 3 days

- [ ] **Add Yahoo Finance fallback**
  - Free historical data
  - Good for research/validation
  - Status: Not started
  - ETA: 2 days

### Strategy Extensions
- [ ] **Support multiple universes**
  - ETFs (current)
  - Large-cap stocks
  - Sector rotation
  - Status: Design phase
  - ETA: 2 weeks

- [ ] **Intraday rebalancing**
  - Hourly bar support
  - Adjust for higher turnover
  - More complex execution logic
  - Status: Research phase
  - ETA: 3 weeks

- [ ] **Machine learning scoring**
  - Alternative to momentum score
  - Feature engineering
  - Model training/validation
  - Status: Research phase
  - ETA: 4 weeks

- [ ] **Multi-account support**
  - Manage multiple accounts
  - Different strategies per account
  - Consolidated reporting
  - Status: Not started
  - ETA: 2 weeks

### Infrastructure
- [ ] **Add CI/CD pipeline**
  - GitHub Actions
  - Automated testing
  - Deployment automation
  - Status: Not started
  - ETA: 1 week

- [ ] **Container registry**
  - Push to Docker Hub or private registry
  - Version tagging
  - Status: Not started
  - ETA: 1 day

- [ ] **Database backend**
  - Replace Parquet with TimescaleDB
  - Better query performance
  - Time-series optimized
  - Status: Research phase
  - ETA: 2 weeks

---

## ✅ Recently Completed

- [x] Core strategy implementation (2025-11-10)
- [x] Backtesting engine (2025-11-10)
- [x] Walk-forward optimization (2025-11-10)
- [x] Permutation testing (2025-11-10)
- [x] IBKR integration (2025-11-10)
- [x] Docker deployment (2025-11-10)
- [x] 208 unit tests (2025-11-11)
- [x] 71% test coverage (2025-11-11)
- [x] Documentation update (2025-11-11)

---

## 🗑️ Deferred / Won't Do

- [ ] ~~Options trading support~~ - Out of scope (cash account, long-only)
- [ ] ~~Shorting capability~~ - Out of scope (cash account)
- [ ] ~~Leverage/margin~~ - Out of scope (cash account)
- [ ] ~~HFT/scalping~~ - Out of scope (daily swing strategy)
- [ ] ~~Custom OMS/EMS~~ - Out of scope (use IBKR)

---

## 📋 Sprint Planning

### Current Sprint (Week of 2025-11-11)
- [ ] Run initial backtest on full dataset
- [ ] Execute walk-forward optimization
- [ ] Run permutation test
- [ ] Start paper trading (dry-run mode)
- [ ] Fix 2 failing tests

### Next Sprint (Week of 2025-11-18)
- [ ] Review paper trading results (week 1)
- [ ] Increase test coverage to 80%
- [ ] Add CLI integration tests
- [ ] Create CHANGELOG.md
- [ ] Set up monitoring

### Future Sprints
- Paper trading validation (ongoing, 3 months)
- Regime detection implementation
- HRP weighting implementation
- Enhanced monitoring & alerting

---

## 📝 Notes

### Test Coverage Strategy
Focus on increasing coverage in these areas:
1. **IBKR client** (76% → 85%): Network error paths, disconnect handling
2. **IBKR execution** (71% → 85%): Order rejection paths, limit order edge cases
3. **Correlation** (67% → 80%): Edge cases with small windows, NaN handling
4. **Permutation** (66% → 80%): Window generation, error handling

### Paper Trading Checklist
Before starting paper trading:
- [x] Docker image builds
- [x] All lints pass
- [x] Type checking passes
- [x] Tests at 99% pass rate
- [ ] Run initial backtest
- [ ] Run walk-forward
- [ ] Run permutation test
- [ ] Document expected performance
- [ ] Set up monitoring/logging

### Parameter Freeze Criteria
Freeze parameters when:
1. Walk-forward Calmar > 0.5
2. Permutation test p-value < 0.05
3. Out-of-sample Sharpe > 1.0
4. Max drawdown < 20%
5. Turnover < 2x/month

---

## 🏷️ Labels

- 🔴 Critical: Must complete before live trading
- 🟡 High: Significantly improves quality/safety
- 🟢 Medium: Nice to have, moderate value
- 🔵 Low: Future enhancement, low urgency
- ✅ Done: Completed
- 🗑️ Deferred: Not pursuing

---

**Last Review**: 2025-11-11  
**Next Review**: 2025-11-18  
**Review Frequency**: Weekly





