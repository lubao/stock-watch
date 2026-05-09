# Next Research Targets (2026-05-09)

這份文件定義下一輪 `stock-watch` 研究方向：先把交易規則的「可驗證性」補強，再討論是否改 live gate。

## Current Thesis

目前最值得研究的不是再加更多選股訊號，而是把候選名單轉成更接近真實操作的決策模型。

也就是：

1. 候選股是否有 edge。
2. 進場後是否真的碰到停利/停損線。
3. 不同情境下該給多少倉位。
4. 週報是否能清楚告訴我們「可以升級」、「只能觀察」、或「樣本不足」。

## Research Lanes

### Lane 1: Path Risk / Execution Realism

**Question:** 現在的 `收盤跌破` 風控是否太慢？是否應該改成盤中碰到 stop/trim 就執行？

Current foundation:

- `alert_tracking.csv` now stores forward low/high path values for 1D/5D/20D.
- Weekly `ATR Band Checkpoints` now compares close-based outcomes with touched stop/trim outcomes.

Next metrics:

- `max_favorable_excursion_pct`
- `max_adverse_excursion_pct`
- `trim_before_stop`
- `stop_before_trim`
- `days_to_trim`
- `days_to_stop`
- `close_recovered_after_stop_touch`

Decision trigger:

- Do not upgrade stop/trim execution rules until each target bucket has enough path maturity.
- First checkpoint: `path_n >= 50` for `1D short` and `5D short`.
- Prefer a semi-auto rule first: show `碰線提醒` before making it a hard exit rule.

### Lane 2: Factor / Signal Validation

**Question:** `setup_score`、`risk_score`、`spec_risk_score`、`volume_ratio20`、`ret5_pct`、`pullback_quality` 哪些真的有預測力？

Borrowed pattern:

- `alphalens`-style forward return by factor quantile.
- `vectorbt`-style broad sensitivity sweeps.

Next metrics:

- factor quantile return by `watch_type`
- factor quantile return by `action`
- factor quantile return by `scenario_label`
- top/bottom spread
- monotonicity score
- date concentration / dominant-date share

Decision trigger:

- A factor can become a gate only if it works across multiple signal dates and does not rely on one hot day.
- Minimum proposal criteria:
  - `n >= 30`
  - `signal_dates >= 5`
  - top-minus-bottom spread is positive in both recent and full-history views
  - worst-tail does not worsen materially

### Lane 3: Portfolio Weight / Mode Separation

**Question:** Telegram 是投資模式、portfolio 是交易模式；那它們是否該共用同一套候選分數，還是共用候選但分開 sizing？

Borrowed pattern:

- FinRL-X style weight-centric contract: selection, allocation, timing, and risk overlay should be separable.

Proposed local contract:

- `selection_score`: 是否值得看。
- `entry_state`: 可買、等確認、只觀察、暫不買。
- `risk_budget`: 0 / 0.25 / 0.5 / 1.0 倉。
- `exit_guard`: close-based / touched-based / time-stop.
- `mode`: investment / trading.

Decision trigger:

- Do not let Telegram 投資模式 inherit short swing sizing directly.
- Portfolio trading mode may use stricter touched stop/trim rules earlier, but only as advisory first.

## Public Repo References

| Repo | Useful Pattern | Local Takeaway |
| --- | --- | --- |
| [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | Fast vectorized backtests, parameter sweeps, portfolio/trade analytics, walk-forward robustness. | Borrow sensitivity report shape; do not migrate workflow yet. |
| [quantopian/alphalens](https://github.com/quantopian/alphalens) | Factor quantiles, forward returns, event/factor tear sheets. | Best fit for validating our scores and signal buckets. |
| [ranaroussi/quantstats](https://github.com/ranaroussi/quantstats) | Portfolio risk metrics, drawdowns, rolling stats, HTML tear sheets. | Borrow reporting vocabulary for portfolio risk and realized strategy curve. |
| [kernc/backtesting.py](https://github.com/kernc/backtesting.py) | Compact strategy API and readable trade-stat output. | Borrow trade-stat table shape for simple strategy experiments. |
| [microsoft/qlib](https://github.com/microsoft/qlib) | Full research pipeline: data, model, backtest, risk, portfolio, execution. | Borrow pipeline boundaries, not the heavy ML stack. |
| [AI4Finance-Foundation/FinRL-Trading](https://github.com/AI4Finance-Foundation/FinRL-Trading) | Weight-centric architecture and modular selection/allocation/timing/risk layers. | Good mental model for separating Telegram investment mode from portfolio trading mode. |
| [TonyMa1/walk-forward-backtester](https://github.com/TonyMa1/walk-forward-backtester) | Walk-forward optimization and robust position management. | Useful reference for future out-of-sample validation shape. |

## Near-Term Implementation Order

1. Add path-risk outcome tables:
   - `max_adverse/favorable excursion`
   - touched stop/trim sequencing
   - close recovery after touch

2. Add factor tear-sheet tables:
   - factor quantiles by `watch_type`
   - factor quantiles by `action`
   - top/bottom spread and date concentration

3. Add mode contract columns:
   - `entry_state`
   - `risk_budget`
   - `exit_guard`
   - `mode`

4. Add weekly decision panel:
   - `Ready to Promote`
   - `Keep Shadow`
   - `Need More Samples`
   - `Blocked by Tail Risk`

## Non-Goals

- Do not add ML/RL dependency now.
- Do not adopt a full backtesting framework unless our local engine cannot express an experiment.
- Do not automate live exits from path-touch data yet.
- Do not loosen short or midlong gates just because one metric improves.

## Working Decision

下一步先做 Lane 1。

Reason: we just started recording true forward path data, and it directly answers the current operational question: stop/trim should be close-based, touched-based, or advisory-only.
