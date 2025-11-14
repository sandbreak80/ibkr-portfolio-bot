# IBKR Fractional Swing Portfolio — Production-Grade System

**Goal:** A production-ready, **long-only**, **fractional**, **correlation-aware** swing-trading system using **Interactive Brokers (IBKR)** via **ib_insync**, with daily rebalancing at **15:55 ET**, **cash-account discipline** (no leverage/shorting, PDT-safe), and rigorous research tooling (backtest, walk-forward, permutation tests).
**Account:** Start on **IBKR Paper** — **`DUK200445`** (~$25k). Later support both paper and live via config switch.
**Universe:** Liquid **ETFs** only (expandable); default list provided.

No fluff. Explicit rules. Deterministic outputs. Strict guardrails.

---

## 📚 Documentation Navigation

This is the **complete technical specification**. For other documentation:

- **[../README.md](../README.md)** - Quick start guide and project overview
- **[../PROJECT_STATUS.md](../PROJECT_STATUS.md)** - Current build health and test status
- **[../TODO.md](../TODO.md)** - Task list and roadmap
- **[context/memory.md](context/memory.md)** - Detailed notes, design decisions, and lessons learned

---

## 0) TL;DR Quick Start

```bash
# 0. System deps (Ubuntu/Debian-like)
sudo apt-get update && sudo apt-get install -y build-essential libssl-dev libffi-dev python3-dev

# 1. Clone project and enter
git clone <YOUR_REPO_URL> ibkr-portfolio-bot && cd ibkr-portfolio-bot

# 2. Build dev container
make build   # builds Docker image, installs Poetry deps

# 3. Configure (copy defaults)
cp .env.example .env
cp config/config.yaml config/config.local.yaml  # edit if needed

# 4. Ensure IBKR TWS/Gateway is running (paper), API port 7497, clientId matches config
#    Paper account must show DUK200445; enable "Read-Only API" for safety while testing.

# 5. Sanity connect
docker compose run --rm app poetry run bot connect

# 6. Fetch historical (default: IBKR delayed mode; cached to Parquet)
docker compose run --rm app poetry run bot fetch

# 7. Backtest (daily bars, lagged signals, costs)
docker compose run --rm app poetry run bot backtest

# 8. Walk-forward and permutation tests
docker compose run --rm app poetry run bot walkforward
docker compose run --rm app poetry run bot permute

# 9. Generate target weights (as-of date)
docker compose run --rm app poetry run bot weights --asof 2024-12-31

# 10. Dry-run orders for paper account
docker compose run --rm app poetry run bot trade --dry-run --paper
```

Artifacts appear under `reports/` (metrics JSON, plots, logs, weights CSV).

---

## 1) Scope & Non-Goals

**In scope**

* Daily swing/rotation among liquid ETFs
* Fractional position sizing
* Correlation-capped selection; inverse-volatility weights
* IBKR-first: data + orders (paper/live)
* Deterministic research workflow (backtest, WF, permutation)

**Out of scope**

* Intraday HFT/scalping, leverage, shorting, options
* Custom OMS/EMS/risk servers
* Vendor lock-in data feeds (project runs with IBKR delayed historicals by default)

---

## 2) System Architecture

```
ibkr-portfolio-bot/
  README.md
  pyproject.toml
  docker/
    Dockerfile
  docker-compose.yml
  Makefile
  .env.example
  config/
    config.yaml            # defaults
    config.local.yaml      # your overrides (gitignored)
  data/
    parquet/               # cached OHLCV
  reports/                 # metrics, plots, logs, weights
  src/
    core/
      config.py            # load/merge config, env overrides
      logging.py           # structured logs, JSONL audit
      clock.py             # US market calendar (XNYS), ET handling
      types.py             # dataclasses / TypedDicts
    brokers/
      ibkr_client.py       # ib_insync connect, marketDataType, historical fetch, pacing/backoff
      ibkr_exec.py         # weights->fractional orders; DAY; dry-run/live/paper
      adapters/
        tiingo_client.py   # optional hist fallback (disabled by default)
        alpaca_client.py   # optional hist fallback (disabled by default)
    data/
      cache.py             # Parquet read/write; idempotent append
      universe.py          # ETF defaults, validators, (optional) scanner stub
      ingestion.py         # orchestrates fetch + cache for all symbols
    features/
      indicators.py        # EMA, ATR, STDEV, MACD (from scratch)
      scoring.py           # ((C/EMA20)-1) / max(ATR% , eps)
      correlation.py       # rolling corr matrix; greedy cap
    strategy/
      signals.py           # long_ok gates and exits
      selector.py          # rank + correlation cap select Top N
      weighting.py         # inverse-vol weights + caps + cash buffer
      backtest.py          # bar-return engine; lagged positions; costs
      walkforward.py       # rolling train/OOS re-opt
      permutation.py       # IMCPT-lite joint permutations
      risk.py              # position limits, sanity checks
      compliance.py        # settlement guard, PDT counter, 1-rebalance/day
    cli.py                 # click CLI: connect/fetch/backtest/walkforward/permute/weights/trade
  tests/
    test_indicators.py
    test_selection.py
    test_backtest.py
    test_walkforward.py
    test_permutation.py
    test_compliance.py
```

**Key design principles**

* Pure functions, explicit inputs/outputs
* Deterministic seeds
* No look-ahead: positions lag returns by +1 bar
* Research parity with live logic (same selection/weights)

---

## 3) Configuration

All runtime behavior comes from `config/config.yaml` merged with `config/config.local.yaml`.

### 3.1 Default config (abridged)

```yaml
ibkr:
  host: "127.0.0.1"
  port: 7497                 # TWS paper default
  client_id: 17
  account_paper: "DUK200445" # paper account id (25k)
  account_live: ""           # set later
  market_mode: "delayed"     # live|delayed|delayedFrozen
  timeframe: "1 day"
  start: "2015-01-01"
  end: null

universe: [SPY, QQQ, VTI, TLT, IEF, GLD, XLE, BND, BITO]

rebalance:
  schedule_et: "15:55"       # HH:MM America/New_York
  frequency: "daily"

costs:
  commission_per_share: 0.0035
  slippage_bps: 1.0

features:
  atr_window: 20
  ema_fast: 20
  ema_slow: 50
  macd:
    enabled: false
    fast: 12
    slow: 26
    signal: 9

selection:
  top_n: 2
  corr_window: 90
  corr_cap: 0.7
  min_score: 0.0

weights:
  method: "inv_vol"
  vol_window: 20
  max_weight_per_asset: 0.5
  cash_buffer: 0.05

backtest:
  seed: 42
  metrics: [CAGR, Sharpe, Calmar, MaxDD, PF, Turnover]

walkforward:
  train_years: 3
  oos_months: 3
  reoptimize:
    ema_fast: [10,20,30]
    ema_slow: [40,50,80]
    top_n: [1,2,3]
    corr_cap: [0.6,0.7,0.8]

permutation:
  runs: 200
  objective: "Calmar"

execution:
  live: false                # dry-run or paper by default
  order_type: "MKT"         # MKT | LMT
  limit_offset_bps: 2
  max_orders_per_day: 5
```

### 3.2 Environment

`.env.example` (copy to `.env` and edit as needed)

```
IB_HOST=127.0.0.1
IB_PORT=7497
IB_CLIENT_ID=17
IB_ACCOUNT_PAPER=DUK200445
IB_ACCOUNT_LIVE=
```

Runtime merges: env → `config.local.yaml` → default `config.yaml`.

---

## 4) IBKR Connectivity & Data Modes

* **TWS/Gateway** must be running (Paper first).
* **API settings**: enable socket clients, read-only API when testing.
* **Market Data Type**:

  * `live` (1): requires subscriptions for real-time
  * `delayed` (3) / `delayedFrozen` (4): **default**, no paid subs needed
* **Historical API limits**: project chunk-requests (e.g., 1y blocks for daily), exponential backoff on HMDS pacing.
* **Caching**:

  * Data normalized to UTC index with columns `[open, high, low, close, volume]`
  * Written to `data/parquet/<SYMBOL>.parquet`, append-safe
  * Idempotent ingestion: only missing dates requested

---

## 5) Strategy Definition (Hard Rules)

### 5.1 Indicators (from scratch)

* `EMA(n)` — standard recursive smoothing
* `ATR(n)` — Wilder’s true range over n
* `STDEV(n)` — sample standard deviation over returns
* `MACD(12,26,9)` — optional gate

### 5.2 Score (per asset at rebalance time *t*)

* `ema_fast = EMA20`
* `ema_slow = EMA50`
* `atr_pct = ATR20 / Close`
* **Score**: `((Close/EMA20) - 1) / max(atr_pct, 1e-6)`

### 5.3 Trend Gate

* `long_ok = (EMA20 > EMA50)`
* Optional: require `MACD > 0` via config

### 5.4 Selection (Top N with correlation cap)

* Rank by `score` desc
* Greedy selection until **N=2** assets chosen
* Before adding asset j, require for all selected k: `|ρ(j,k)| ≤ 0.7` using **rolling 90-day return correlations**
* If no asset passes gates → hold cash

### 5.5 Weighting

* Inverse-volatility weighting:

  * `vol_i = stdev(returns, window=20)`
  * `w_i ∝ 1/vol_i`
  * Normalize weights; **cap 50% per asset**; **5% cash buffer**
* Target gross exposure ≤ 1.0 × equity

### 5.6 Entries/Exits/Rebalance

* **Entry**: on the **next bar** after selection (positions **lag +1** bar)
* **Exit**: if `Close < EMA20` or asset falls out of correlation-capped Top N
* **Rebalance**: **once per day at 15:55 ET**; no intraday round-trips

---

## 6) Compliance, Risk & Execution

### 6.1 Cash-Account Discipline

* Long-only, no leverage/shorting
* **Settlement guard**: `target_notional ≤ settled_cash` before placing orders
* Defensive **PDT counter** (even though cash is exempt)
* **Max orders/day = 5**

### 6.2 Order Construction

* Convert weights to target notionals from equity or `AvailableFunds` after **cash buffer**
* Convert to **fractional qty**
* Orders: `DAY`; `MKT` (default) or `LMT` (price = mid ± `limit_offset_bps`)
* Regular hours only

### 6.3 Execution Modes

* `--dry-run`: compute orders, print, **no routing**
* `--paper`: route via **`DUK200445`**
* `--live`: route to live account id (set in config/env)

---

## 7) Backtesting Engine

### 7.1 Bar-Return Method (No Look-Ahead)

* Align assets by date
* Compute per-asset **position_t** (weights or 0), then **lag by +1 bar**
* Strategy return = `position_{t-1} * return_t − costs_t`
* Aggregate across assets

### 7.2 Costs

* Commission/share (default 0.0035)
* Slippage haircut in **bps** of notional (default 1 bp)
* Turnover-proportional (apply when weights change)

### 7.3 Metrics

* CAGR
* Sharpe (rf=0)
* Max Drawdown (peak-to-trough)
* Calmar (CAGR / MaxDD)
* Profit Factor (gross gains / gross losses)
* Turnover (Σ|Δweight|)

### 7.4 Plots & Reports

* `equity.png`, `drawdown.png`, `heatmap.png` (monthly returns)
* `metrics.json` (all KPIs)
* `weights.csv` (date, symbol, weight)
* JSONL audit logs in `reports/logs/` with: timestamp, inputs, selected assets, corr summary, weights, orders (if any)

---

## 8) Walk-Forward & Permutation Testing

### 8.1 Walk-Forward (WF)

* **Train** `N` years (default 3) → **OOS** `M` months (default 3)
* Grid search over:

  * `ema_fast ∈ {10,20,30}`
  * `ema_slow ∈ {40,50,80}`
  * `top_n ∈ {1,2,3}`
  * `corr_cap ∈ {0.6,0.7,0.8}`
* Select params on train objective (Calmar by default), apply to next OOS
* Concatenate OOS segments to form WF equity

### 8.2 IMCPT-Lite (Permutation)

* **Joint permutations** inside each train window to **preserve cross-asset structure** across assets while breaking time order
* For each run (N=200):

  * Permute train
  * Re-opt grid on permuted train
  * Record best objective
* **p-value** = fraction of permuted best scores ≥ real best score
* Interpretation: small p suggests real structure vs selection noise

---

## 9) Universe Management

### 9.1 Default ETFs

* `SPY` (US large-cap), `QQQ` (tech), `VTI` (broad US),
  `TLT` (long UST), `IEF` (intermediate UST), `BND` (agg bonds),
  `GLD` (gold), `XLE` (energy), `BITO` (BTC proxy)
* Criteria: liquidity, low spread, capacity, distinct exposures

### 9.2 Correlation Reality

* Correlations **shift by regime**; rolling 90D matrix used
* Correlation cap prevents duplicates (e.g., SPY vs VTI at 0.95)
* In crises, corr→1: system falls back to fewer positions + more cash

---

## 10) CLI Commands

```text
connect      Verify TWS/Gateway, set marketDataType, print account summary.
fetch        Fetch/update OHLCV to Parquet (IBKR delayed default); pacing-safe.
backtest     Run daily backtest on cache; produce metrics/plots/logs/weights.
walkforward  Rolling train/OOS with grid; output OOS metrics + chosen params.
permute      IMCPT-lite on train windows; N runs; print p-value.
weights      Print target weights JSON as of a date (fractional-ready).
trade        Build orders from weights; --dry-run | --paper | --live modes.
```

**Examples**

```bash
poetry run bot connect
poetry run bot fetch --start 2018-01-01 --end 2025-11-01
poetry run bot backtest
poetry run bot walkforward
poetry run bot permute --runs 200
poetry run bot weights --asof 2024-12-31
poetry run bot trade --dry-run --paper
```

---

## 11) Logging, Audit & Determinism

* Structured logs to stdout + JSONL audit under `reports/logs/`
* Every rebalance event: snapshot of inputs → selection → weights → (orders)
* Seed all stochastic steps (`backtest.seed`, numpy/pandas)
* Reproducible WF & permutation outputs given same data & config

---

## 12) Testing & Quality Gates

### 12.1 Unit / Integration Tests

* **Indicators**: compare EMA/ATR/STDEV/MACD vs known vectors
* **Selection**: synthetic corr matrices verify cap enforcement
* **Backtest**: mutate future bar → **past signals unchanged** (no look-ahead)
* **WF**: OOS concatenation length & timestamps; no leakage
* **Permutation**: p in [0,1]; deterministic with seed
* **Compliance**: settlement guard prevents illegal orders; one rebalance/day; caps respected
* **Execution (mock)**: fractional qty computation, LMT pricing from mid, max orders/day throttling

### 12.2 CI (GitHub Actions)

* `ruff` lint, `mypy` type check, `pytest` unit/integration
* Optional nightly job: `fetch + backtest`; upload `reports/` artifacts

---

## 13) Makefile & Docker

**Makefile targets**

```
make build      # build Docker image, poetry install
make lint       # ruff
make type       # mypy
make test       # pytest
make fetch      # run fetch
make backtest   # run backtest
make wf         # walk-forward
make permute    # permutation test
```

**Docker assumptions**

* `app` service runs Poetry in a Python 3.11-slim base with `pyarrow`, `matplotlib` system deps
* Mount repo into container; TWS/Gateway exposed on host 127.0.0.1:7497

---

## 14) Error Handling & Pacing

* **HMDS Pacing**: exponential backoff on pacing errors; chunk historical spans (e.g., 365-day blocks)
* **Partial Data**: if symbol lacks full history, engine aligns on intersection of available dates; missing assets yield 0 weight that day
* **Network/Session**: auto-reconnect to ib_insync; fail gracefully if connect fails (non-zero exit)
* **Order Rejections**: on live/paper, log full error, halt trading loop; never retry blindly

---

## 15) Extensibility

* **Universe**: add/remove tickers in `config.yaml`
* **Signals**: drop a new scoring function in `features/scoring.py` and reference in config
* **Weights**: add `HRP` or `ERC` in `strategy/weighting.py` (behind config flag)
* **Regime Overlay**: add SPX<200DMA & VIX threshold dampener in `signals.py` or `risk.py`
* **Hourly Bars**: set `ibkr.timeframe: "1 hour"` (research only; expect turnover ↑)

---

## 16) Acceptance Criteria (Hard)

* `make build && make fetch && make backtest` completes with defaults, producing:

  * `reports/metrics.json` (CAGR, Sharpe, Calmar, MaxDD, PF, Turnover)
  * `reports/equity.png`, `reports/drawdown.png`, `reports/heatmap.png`
  * `reports/weights.csv`
  * JSONL logs under `reports/logs/`
* Signals are **lagged +1 bar** (test enforces no look-ahead)
* Default turnover ≤ ~4 rebalances/month
* WF & permutation commands run and produce deterministic outputs with given seed
* `trade --dry-run` prints compliant fractional orders; `--paper` routes to **`DUK200445`**; `--live` exists but off by default

---

## 17) Pseudocode (Ground Truth)

**Selection + Weights (per rebalance date t):**

```python
scores = ((close/ema20) - 1) / np.maximum(atr20/close, 1e-6)
rank = scores.sort_values(ascending=False)

selected = []
for sym in rank.index:
    if not long_ok[sym]: 
        continue
    if all(abs(rolling_corr.loc[sym, k]) <= corr_cap for k in selected):
        selected.append(sym)
    if len(selected) == top_n:
        break

if not selected:
    target_weights = {}
else:
    vols = {s: returns[s].rolling(vol_window).std().iloc[-1] for s in selected}
    inv_vol = {s: 1.0/max(vols[s], 1e-9) for s in selected}
    w = normalize_with_caps(inv_vol, max_weight_per_asset, cash_buffer)
    target_weights = w
```

**Backtest (lagged positions):**

```python
positions_t = target_weights_t  # 0 for non-selected
positions_lagged = positions_t.shift(1).fillna(0)
gross_returns = (positions_lagged * asset_returns).sum(axis=1)

turnover = (positions_t - positions_t.shift(1)).abs().sum(axis=1).fillna(0)
costs = commissions(turnover, commission_per_share) + slippage(turnover, slippage_bps)

portfolio_returns = gross_returns - costs
```

---

## 18) Glossary

* **Bar-return engine**: compute returns using lagged positions to avoid look-ahead
* **IMCPT-lite**: in-sample Monte-Carlo permutation test; here, applied to train windows with joint permutations
* **WF**: walk-forward, rolling re-optimization to estimate OOS performance honestly
* **PDT**: Pattern Day Trader rule; not applicable to cash accounts, tracked here defensively

---

## 19) Known Limitations

* IBKR delayed data timestamps vs exchange holidays: minor misalignments possible
* BITO/crypto proxies differ from spot BTC; treat as an equity-like exposure with unique roll yield
* Correlations converge in crises; correlation cap reduces duplication but cannot eliminate systemic sell-offs
* Taxes not modeled; turnover may have implications in taxable accounts

---

## 20) Operational Notes (Paper → Live)

* Paper first (account **`DUK200445`**), run for months
* Freeze strategy/params after WF success; no param-churn post go-live
* Live switch: set `execution.live: true` and `ibkr.account_live` to your live id
* Keep **read-only** API toggle while validating; enable trading only with full logs and safeguards observed

---

## 21) Issue Templates (Cut-and-Paste)

**Bug: No-Look-Ahead Violation**

* Symptom:
* Repro steps:
* Expected vs actual:
* Data sample:
* Hash/commit:

**Enhancement: Add HRP Weights**

* Rationale:
* API changes:
* Acceptance tests:
* Risk:

---

## 22) What “Done” Looks Like

* Deterministic research runs produce stable metrics; p-value from permutation < 5–10% on train windows
* WF OOS metrics acceptable (define your bar: e.g., Calmar ≥ 0.5, MaxDD ≤ 20%, Turnover ≤ 1×/mo)
* Dry-run orders are compliant and traceable; paper fills look sane; settlement guard blocks illegal sizing
* CI green: lint/type/tests pass; Docker image builds; nightly backtest artifacts available

---

If you follow this README, a coding agent can scaffold, implement, test, and operate the system **end-to-end** without ambiguity.
