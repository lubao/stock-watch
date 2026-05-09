# Roadmap From Repo Review (2026-05-09)

這份 roadmap 根據目前 `stock-watch` 的狀態，以及參考 vectorbt / alphalens / QuantStats / backtesting.py / Qlib / FinRL-X 後的差距整理而成。

目標不是把系統變成大型量化平台，而是讓它從「研究輔助」逐步走向「半自動操作決策」。

## North Star

把每日候選名單轉成可驗證、可解釋、可控風險的操作建議：

```text
候選股 → 情境判斷 → 進場狀態 → 倉位建議 → 停利/停損提醒 → 事後驗證 → 規則升級/封存
```

## Current Position

目前系統已經完成：

- snapshot → outcome → weekly review 的資料閉環。
- `可小試 / 可等買點 / 暫不買 / 只觀察` 這類操作語言。
- `0 / 0.25 / 0.5` 倉位語言。
- forward low/high path tracking。
- ATR Band Checkpoints with touched stop/trim + MFE/MAE。
- 投資模式與交易模式的初步分離概念。

但還缺：

- 完整碰線順序：先停利還是先停損。
- factor tear sheet：哪些分數真的有預測力。
- portfolio-level risk panel：持倉整體風險與回撤。
- trade-level simulation：entry / sizing / exit / P&L。
- decision panel：哪些規則 ready、哪些只觀察、哪些 blocked。

## Phase 1: Path Risk 第二層

**目的：** 把目前的 `有沒有碰 stop/trim` 升級成 `怎麼碰、先碰誰、碰完是否收回來`。

### Deliverables

1. `trim_before_stop`
2. `stop_before_trim`
3. `days_to_trim`
4. `days_to_stop`
5. `close_recovered_after_stop_touch`
6. `close_failed_after_trim_touch`
7. Weekly `Path Risk Sequencing` table

### Why First

這直接回答目前最靠近操作的問題：

- 停損要用收盤？盤中碰到？還是先提醒？
- 停利要等收盤？碰線分批？還是只做觀察？
- short swing 的風險是否其實來自路徑，而不是最後報酬？

### Decision Gate

先不自動交易，只升級成提醒。

可以討論升級成規則的條件：

- `path_n >= 50`
- `stop_before_trim_rate` 穩定偏低
- `recovery_after_stop_touch_rate` 不高
- 不集中在單一 signal date

## Phase 2: Factor Tear Sheet

**目的：** 像 alphalens 一樣驗證我們自己的分數/標籤，而不是憑直覺相信它們。

### Factors To Test

- `setup_score`
- `risk_score`
- `spec_risk_score`
- `volume_ratio20`
- `ret5_pct`
- `ret20_pct`
- `atr_pct`
- `pullback_quality`
- `action_label`
- `scenario_label`

### Deliverables

1. Quantile return table by factor
2. Top-bottom spread
3. Monotonicity score
4. Tail risk by quantile
5. Date concentration check
6. Weekly `Factor Tear Sheet` section

### Decision Gate

某 factor 可以升級成 gate 的條件：

- `n >= 30`
- `signal_dates >= 5`
- top-bottom spread 在 recent / full 都同向
- tail risk 沒明顯惡化
- 不只是 hot market 的副產品

## Phase 3: Portfolio Risk Panel

**目的：** 把 portfolio 從「逐檔建議」升級成「整體部位風險」。

參考 QuantStats 的方向，但不急著引入 dependency。

### Deliverables

1. Current exposure by group / layer / mode
2. High-risk exposure share
3. Stop-distance weighted risk
4. Portfolio drawdown proxy
5. Position-level heat map
6. `投資模式` vs `交易模式` 分開顯示

### Decision Gate

當 portfolio panel 能回答下面問題，就可以進入下一階段：

- 現在整體太熱嗎？
- 哪些持倉拖累風險最多？
- 是否該先降風險，而不是找新標的？
- Telegram 的投資建議是否和 portfolio 的交易風控衝突？

## Phase 4: Trade-Level Simulation

**目的：** 從 N 日 forward return 進化到 entry / sizing / exit / P&L。

參考 backtesting.py 的 trade-stat 形式，但保留本地簡單實作。

### Candidate Strategies

1. `高風險拉回 + 隔日轉強 + 0.25 倉`
2. `健康拉回 + 支撐確認 + 0.5 倉`
3. `開高不追 shadow promotion`
4. `portfolio trading mode touched stop/trim advisory`

### Deliverables

1. Trade ledger
2. Win rate
3. Avg win / avg loss
4. Profit factor
5. Expectancy
6. Max adverse excursion before exit
7. Rule comparison table

### Decision Gate

可以考慮正式調整 live rule 的條件：

- rule-level sample 不再過小
- profit factor > 1 且 tail 可控
- touched-stop simulation 不比 close-stop 更糟
- recent / full 不互相矛盾

## Phase 5: Decision Panel

**目的：** 讓週報直接告訴我們要不要決策，而不是每次人工讀表。

### Buckets

1. `Ready to Promote`
2. `Keep Shadow`
3. `Need More Samples`
4. `Blocked by Tail Risk`
5. `Retire / Ignore`

### Deliverables

1. Weekly decision panel
2. Rule status history
3. Promotion criteria per rule
4. Auto-generated next action

## Implementation Order

### Sprint A: Path Risk Sequencing

- Add path sequencing columns or derived table.
- Add weekly `Path Risk Sequencing` section.
- Keep output advisory-only.

### Sprint B: Factor Tear Sheet MVP

- Start with `setup_score`, `risk_score`, `spec_risk_score`, `volume_ratio20`, `ret5_pct`.
- Add quantile and top-bottom spread tables.

### Sprint C: Portfolio Risk Panel MVP

- Add exposure by mode / group / layer.
- Add stop-distance weighted risk.
- Separate investment vs trading language.

### Sprint D: Trade Simulation MVP

- Implement only one strategy first: `高風險拉回 + 隔日轉強 + 0.25 倉`.
- Compare touched-stop vs close-stop.

### Sprint E: Weekly Decision Panel

- Convert diagnostics into rule statuses.
- Surface only decisions that need human review.

## What Not To Do Yet

- Do not import Qlib / FinRL-X.
- Do not train ML/RL models.
- Do not run massive parameter optimization before path/factor basics are clean.
- Do not automate sell orders.
- Do not loosen live gates based on one table.

## Next Immediate Step

Start Sprint A.

Build `Path Risk Sequencing` so weekly review can answer:

- 先碰停利還是先碰停損？
- 碰停損後是否常常收回？
- 盤中碰線提醒是否比收盤規則更合理？
