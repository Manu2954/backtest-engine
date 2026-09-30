# Backtest Engine — Honest Assessment (2026-09-28)

**What this is:** a candid "what's good / what's not / how close to the real world"
review, grounded in a full-codebase pass (7 parallel reviews covering engine core,
indicators/reporting, robustness, API/tasks/models, providers, and both frontend
layers) plus hand-verified reproduction of the top financial bugs
(`backend/tests/unit/test_financial_correctness_repro.py`).

**Deployment assumption:** single-user / localhost. Security findings
(no auth, default DB creds, R service on 0.0.0.0) are therefore treated as
defense-in-depth, NOT active risk. If that ever changes, re-read the Security
section — auth/IDOR becomes the #1 blocker.

**Relationship to `LIVE_TRADING_FEASIBILITY_ANALYSIS.txt` (2026-03-16):** that doc
rates go-live confidence at 85%. This assessment is more cautious. The architecture
claim holds up; the "engine logic is production-ready" claim does not survive a
line-level correctness pass (see lookahead + benchmark/Sortino bugs below). Treat
that doc as an architecture roadmap, this one as a correctness reality check.

---

## The verdict in one paragraph

The engine is **well-architected, defensively coded, and clearly the product of many
real bug-fix cycles** (ATTR-*, SIZE-*, DYN-*, EXIT-*, DATA-002 markers everywhere).
The core mechanics that usually kill amateur backtesters — signal/fill timing,
position & PnL accounting, commission, stop/TP ordering, gap fills — are **correct**.
But it still carries **several silent result-corrupting bugs** (a Redis cache-key
collision, an incomplete-daily-bar lookahead, a phantom benchmark bar-0 return, a
wrong Sortino formula) and **one methodological trap** (non-causal regime labels).
None of these throw errors; they just make the numbers wrong. **As a research/backtest
tool it is close to trustworthy once the four verified bugs are fixed. As a live-trading
system it is far — there is no event loop, no live feed, and no broker integration.**

---

## What is GOOD (verified, not assumed)

**Engine execution path — the hard part is right.**
- Signals are latched at end of bar `i` and filled at bar `i+1` open. No same-bar
  close-decision-then-close-fill lookahead in the main loop. This is the single most
  common backtest error and it is handled correctly.
- Position accounting, PnL, and commission: commission applied once on entry and once
  on exit; short-collateral and leverage/margin/liquidation math internally consistent.
  No double-counting found.
- Stop-loss takes priority over take-profit on the same bar; liquidation checked first
  for leveraged positions; gap-through fills are realistic (worse for stops, better for
  TP). Correct.
- Division-by-zero is guarded throughout the hot path.

**Indicators.** All delegate to `pandas_ta` with correct params; warmup detection is
correct (first bar where ALL indicators are non-NaN); no `.shift()` misuse, no centered
windows, no forward-fill leaking the future. Heikin-Ashi recursion is causal.

**Robustness — the parts that matter for overfitting-avoidance.** Walk-forward windows
are disjoint, contiguous, non-optimizing — no in-sample/out-of-sample overlap.
Parameter-sensitivity isolates state via `deepcopy` (no bleed between runs).

**Web/persistence hygiene.** No SQL injection (all ORM/bound params). No eval/pickle/
unsafe-yaml. DB sessions are managed correctly (`async with`, per-task NullPool engine
disposed in `finally`). N+1 avoided via `selectinload`. Global exception handlers return
sane statuses and log — errors are not silently swallowed.

**Frontend main app.** The shadcn/Tailwind core (Sidebar, AppShell, charts, forms) is
solid: no XSS (`dangerouslySetInnerHTML` absent), no committed secrets, stable list keys,
chart timestamps normalized without timezone shift. Repo hygiene is clean — no tracked
build artifacts, data, caches, or `.env`.

**Providers.** OHLCV column mapping, timestamp units (ms→naive-UTC), bar labeling, and
ordering are correct for Binance. Timeouts present.

---

## What is NOT good

### Result-corrupting bugs (verified, reproduced — fix before trusting output)
1. **Redis cache-key collision** — `data_layer.py:219`. Key omits asset_class / provider /
   market_type / timezone. Fetch a symbol as SPOT then FUTURES and the second call returns
   the first's cached prices. Silent, order-dependent. *(DB layer keys correctly; Redis
   layer does not.)*
2. **Incomplete daily-bar lookahead** — `data_layer.py:305`. The incomplete-bar filter
   only runs for intraday resolutions; a still-forming `1d`/`1w`/`1mo` bar (non-final
   high/low/close) is kept when a backtest ends "today."
3. **Benchmark phantom bar-0 return** — `report_generator.py:54-57`.
   `equity[0] = capital·close[0]/open[0]`, not `capital`. Verified: with
   open=100/close=110/final=120, reported benchmark return is **9.1%** vs correct **20%**.
   Affects benchmark return + alpha (level metrics); benchmark Sharpe/beta are unaffected.
   *(The existing `test_benchmark_alignment.py` enshrines this bug and only passes because
   its fixture has open[0]≈close[0].)*
4. **Sortino formula** — `report_generator.py:280`. Uses std of the downside subset about
   its own mean, not RMS of shortfalls below target; a single down-day yields `None`.

Reproduction tests for all four: `backend/tests/unit/test_financial_correctness_repro.py`
(currently `xfail(strict=True)` — they flip to hard errors the moment each bug is fixed).

### Methodological trap (document loudly, or make causal)
5. **Non-causal regime labels** — `robustness/regime_detection.py`. Regime label for bar
   *t* is derived from the whole series (future included), then used to bucket trade
   entries. Fine as descriptive post-hoc analysis; a real leak if any entry filter consumes
   these labels. Same disease in the L1 strategy (global fit ⇒ labels depend on total series
   length). Not unit-testable deterministically; needs an expanding-window detector or a
   loud "must not feed entry logic" contract.

### Secondary correctness (real, lower blast radius)
- Segment features recompute returns per-segment → drop the boundary bar; short segments
  get `mean_vol=0` and mislabel, distorting the median used to label *all* segments.
- PELT `changepoints[-1] = len(df)` overwrite can delete a real boundary or IndexError.
- Binance `1mo` stepped as fixed 30 days → duplicate/missing monthly bars; no post-page dedup.
- yfinance does no UTC normalization → cross-provider timestamp misalignment.
- Last-bar pending entries are filled then force-closed same bar → phantom slippage/commission
  loss on a zero-duration trade.
- Robustness endpoints poll the DB in-request (racy; false HTTP 500 on slow workers).
- No Celery task idempotency / orphan-run recovery; non-idempotent trade inserts.

### Frontend correctness (the robustness+comparison cluster)
- One real crash: conditional React hook in `ConditionGroupFocusModal`.
- Two systemic families: financial-zero treated as missing (`value ? … : '—'`, `value || 0`)
  so a legit 0% shows "—" or red; and async effects with no ignore/abort flag (stale response
  overwrites fresh state). WalkForwardResults multiplies an already-percent value by 100
  (12.5% → 1250%) and crashes on missing `assessment`.

### Security (parked — single-user localhost)
No auth/authz on any endpoint (IDOR), default `backtest:backtest` DB creds, R service bound
to 0.0.0.0 with no auth or input bounds. **Not active risk for localhost single-user.** These
become blockers only if the app is ever networked or multi-tenant.

---

## How close is this to the real world?

### As a research / backtesting tool: **CLOSE** (weeks, not months)
The execution engine is fundamentally sound. The gap is a **short list of specific,
verified bugs**, not a design flaw. Fix the four result-corruptors (#1–#4), decide the
regime-label contract (#5), and the numbers become trustworthy. The reproduction tests
already define "done." Biggest residual risk after that: the benchmark/alpha and robustness
outputs, which are the least battle-tested surfaces.

### As a live / automated-trading system: **FAR** (months, and a different architecture)
This is a **batch, bar-by-bar** engine. Live trading needs things that do not exist here:
- **Event-driven loop** instead of "iterate a DataFrame" — the current structure assumes the
  whole price history is present up front.
- **Real-time data feed** (websocket/streaming) — providers here are REST pull, and the
  Binance client is *synchronous inside `async def`* (blocks the event loop).
- **Broker/exchange order integration** — none. No order lifecycle, no reconciliation, no
  partial-fill handling against a real venue, no rejects/retries.
- **State durability & recovery** — no orphan-run recovery today; a live system must survive
  restarts mid-position.
- **The lookahead bugs are disqualifying for live** — an incomplete-bar or cache-collision
  bug that merely skews a backtest will trade on wrong data in production.

The existing `LIVE_TRADING_FEASIBILITY_ANALYSIS.txt` is right that the *strategy/indicator/
condition logic is reusable* and the architecture is *evolvable*. Its 85% confidence is
optimistic because it assumes the engine logic is already correct; the correctness bugs above
are the tax that optimism skips.

### Honest scorecard
| Area | State | Distance to "real" |
|------|-------|--------------------|
| Signal/fill timing, PnL, costs | Correct | There |
| Indicators | Correct | There |
| Walk-forward / param-sensitivity | Correct | There |
| Data caching & ingestion | **Bugged** (#1, #2, #4-monthly, tz) | Weeks |
| Reporting metrics (benchmark, Sortino) | **Bugged** (#3, Sortino) | Weeks |
| Regime detection | **Non-causal** (#5) | Weeks + a decision |
| Frontend main app | Good | There |
| Frontend robustness/comparison UI | Bugged, lower quality | Weeks |
| Live trading (feed/broker/event loop) | **Absent** | Months + re-architecture |

---

## Recommended order of work
1. Fix #1–#4 (verified, tests exist) — restores trust in backtest numbers.
2. Resolve #5 — decide: descriptive-only contract, or expanding-window detector.
3. Clean up the secondary engine/provider correctness items.
4. Frontend: the two systemic families (financial-zero, async-race) + the hook crash.
5. Only then consider the live-trading track — and treat it as a new system that reuses
   this one's strategy logic, not as a flag flip on this one.
