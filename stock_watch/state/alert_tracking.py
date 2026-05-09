from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import pandas as pd


ALERT_TRACK_COLUMNS = [
    "alert_date",
    "watch_type",
    "ticker",
    "name",
    "group",
    "grade",
    "rank",
    "setup_score",
    "risk_score",
    "layer",
    "signals",
    "regime",
    "action_label",
    "feedback_score",
    "feedback_label",
    "scenario_label",
    "add_price",
    "trim_price",
    "stop_price",
    "alert_close",
    "ret1_future_pct",
    "low1_future_pct",
    "high1_future_pct",
    "trim1_touch_day",
    "stop1_touch_day",
    "trim1_before_stop",
    "stop1_before_trim",
    "same_day1_stop_trim",
    "stop1_recovered_by_close",
    "trim1_failed_by_close",
    "ret5_future_pct",
    "low5_future_pct",
    "high5_future_pct",
    "trim5_touch_day",
    "stop5_touch_day",
    "trim5_before_stop",
    "stop5_before_trim",
    "same_day5_stop_trim",
    "stop5_recovered_by_close",
    "trim5_failed_by_close",
    "ret20_future_pct",
    "low20_future_pct",
    "high20_future_pct",
    "trim20_touch_day",
    "stop20_touch_day",
    "trim20_before_stop",
    "stop20_before_trim",
    "same_day20_stop_trim",
    "stop20_recovered_by_close",
    "trim20_failed_by_close",
    "status",
]


def _first_touch_day(values: pd.Series, threshold: float, *, direction: str) -> int:
    for offset, value in enumerate(values, start=1):
        price = pd.to_numeric(value, errors="coerce")
        if pd.isna(price):
            continue
        if direction == "above" and float(price) >= threshold:
            return offset
        if direction == "below" and float(price) <= threshold:
            return offset
    return 0


def _sequence_payload(
    *,
    closes: pd.Series,
    lows: pd.Series,
    highs: pd.Series,
    idx: int,
    horizon: int,
    trim_price: float,
    stop_price: float,
) -> dict[str, int]:
    high_window = highs.iloc[idx + 1 : idx + horizon + 1]
    low_window = lows.iloc[idx + 1 : idx + horizon + 1]
    future_close = float(closes.iloc[idx + horizon])
    trim_day = _first_touch_day(high_window, trim_price, direction="above")
    stop_day = _first_touch_day(low_window, stop_price, direction="below")
    return {
        f"trim{horizon}_touch_day": trim_day,
        f"stop{horizon}_touch_day": stop_day,
        f"trim{horizon}_before_stop": int(trim_day > 0 and (stop_day == 0 or trim_day < stop_day)),
        f"stop{horizon}_before_trim": int(stop_day > 0 and (trim_day == 0 or stop_day < trim_day)),
        f"same_day{horizon}_stop_trim": int(trim_day > 0 and stop_day > 0 and trim_day == stop_day),
        f"stop{horizon}_recovered_by_close": int(stop_day > 0 and future_close > stop_price),
        f"trim{horizon}_failed_by_close": int(trim_day > 0 and future_close < trim_price),
    }


def upsert_alert_tracking(
    short_candidates: pd.DataFrame,
    midlong_candidates: pd.DataFrame,
    *,
    alert_track_csv: Path,
    market_scenario: Optional[dict],
    yf_period: str,
    feedback_action_label: Callable[[pd.Series, str], str],
    watch_price_plan: Callable[[pd.Series, str], dict],
    yf_download_one: Callable[[str, str], pd.DataFrame],
) -> None:
    if alert_track_csv.exists():
        try:
            hist = pd.read_csv(alert_track_csv)
        except Exception:
            hist = pd.DataFrame(columns=ALERT_TRACK_COLUMNS)
    else:
        hist = pd.DataFrame(columns=ALERT_TRACK_COLUMNS)

    candidate_groups = [
        ("short", short_candidates),
        ("midlong", midlong_candidates),
    ]
    scenario_label = str((market_scenario or {}).get("label", "") or "")

    for watch_type, candidates in candidate_groups:
        if candidates is None or candidates.empty:
            continue
        for _, row in candidates.iterrows():
            alert_date = str(row["date"])
            mask = (
                (hist.get("alert_date", pd.Series(dtype=str)).astype(str) == alert_date)
                & (hist.get("watch_type", pd.Series(dtype=str)).astype(str) == watch_type)
                & (hist.get("ticker", pd.Series(dtype=str)).astype(str) == str(row["ticker"]))
            )
            price_plan = watch_price_plan(row, watch_type)
            payload = {
                "alert_date": alert_date,
                "watch_type": watch_type,
                "ticker": row["ticker"],
                "name": row["name"],
                "group": row["group"],
                "layer": row.get("layer", ""),
                "grade": row["grade"],
                "rank": int(row["rank"]),
                "setup_score": int(row["setup_score"]),
                "risk_score": int(row["risk_score"]),
                "signals": row["signals"],
                "regime": row["regime"],
                "action_label": feedback_action_label(row, watch_type),
                "feedback_score": float(row.get("feedback_score", 0.0)),
                "feedback_label": str(row.get("feedback_label", "樣本不足")),
                "scenario_label": scenario_label,
                "add_price": price_plan.get("add_price"),
                "trim_price": price_plan.get("trim_price"),
                "stop_price": price_plan.get("stop_price"),
                "alert_close": float(row["close"]),
                "ret1_future_pct": None,
                "low1_future_pct": None,
                "high1_future_pct": None,
                "trim1_touch_day": None,
                "stop1_touch_day": None,
                "trim1_before_stop": None,
                "stop1_before_trim": None,
                "same_day1_stop_trim": None,
                "stop1_recovered_by_close": None,
                "trim1_failed_by_close": None,
                "ret5_future_pct": None,
                "low5_future_pct": None,
                "high5_future_pct": None,
                "trim5_touch_day": None,
                "stop5_touch_day": None,
                "trim5_before_stop": None,
                "stop5_before_trim": None,
                "same_day5_stop_trim": None,
                "stop5_recovered_by_close": None,
                "trim5_failed_by_close": None,
                "ret20_future_pct": None,
                "low20_future_pct": None,
                "high20_future_pct": None,
                "trim20_touch_day": None,
                "stop20_touch_day": None,
                "trim20_before_stop": None,
                "stop20_before_trim": None,
                "same_day20_stop_trim": None,
                "stop20_recovered_by_close": None,
                "trim20_failed_by_close": None,
                "status": "OPEN",
            }
            if mask.any():
                hist.loc[mask, list(payload.keys())] = list(payload.values())
            else:
                hist.loc[len(hist), list(payload.keys())] = list(payload.values())

    if not hist.empty:
        open_rows = hist[hist.get("status", pd.Series(dtype=str)).astype(str) != "CLOSED"]
        if not open_rows.empty:
            for ticker, ticker_rows in open_rows.groupby(hist.get("ticker", pd.Series(dtype=str)).astype(str)):
                try:
                    df = yf_download_one(str(ticker), yf_period)
                except Exception:
                    continue
                if df.empty:
                    continue

                closes = df["Close"].reset_index(drop=True)
                lows = df["Low"].reset_index(drop=True) if "Low" in df.columns else None
                highs = df["High"].reset_index(drop=True) if "High" in df.columns else None
                date_to_idx = {dt: idx for idx, dt in enumerate(df.index.strftime("%Y-%m-%d"))}

                for row_idx, row in ticker_rows.iterrows():
                    idx = date_to_idx.get(str(row["alert_date"]))
                    if idx is None:
                        continue
                    entry = float(closes.iloc[idx])

                    if pd.isna(row.get("ret1_future_pct")) and idx + 1 < len(closes):
                        hist.at[row_idx, "ret1_future_pct"] = round((float(closes.iloc[idx + 1]) / entry - 1.0) * 100, 2)
                    if lows is not None and pd.isna(row.get("low1_future_pct")) and idx + 1 < len(lows):
                        hist.at[row_idx, "low1_future_pct"] = round((float(lows.iloc[idx + 1]) / entry - 1.0) * 100, 2)
                    if highs is not None and pd.isna(row.get("high1_future_pct")) and idx + 1 < len(highs):
                        hist.at[row_idx, "high1_future_pct"] = round((float(highs.iloc[idx + 1]) / entry - 1.0) * 100, 2)
                    if pd.isna(row.get("ret5_future_pct")) and idx + 5 < len(closes):
                        hist.at[row_idx, "ret5_future_pct"] = round((float(closes.iloc[idx + 5]) / entry - 1.0) * 100, 2)
                    if lows is not None and pd.isna(row.get("low5_future_pct")) and idx + 5 < len(lows):
                        hist.at[row_idx, "low5_future_pct"] = round((float(lows.iloc[idx + 1 : idx + 6].min()) / entry - 1.0) * 100, 2)
                    if highs is not None and pd.isna(row.get("high5_future_pct")) and idx + 5 < len(highs):
                        hist.at[row_idx, "high5_future_pct"] = round((float(highs.iloc[idx + 1 : idx + 6].max()) / entry - 1.0) * 100, 2)
                    if pd.isna(row.get("ret20_future_pct")) and idx + 20 < len(closes):
                        hist.at[row_idx, "ret20_future_pct"] = round((float(closes.iloc[idx + 20]) / entry - 1.0) * 100, 2)
                        hist.at[row_idx, "status"] = "CLOSED"
                    if lows is not None and pd.isna(row.get("low20_future_pct")) and idx + 20 < len(lows):
                        hist.at[row_idx, "low20_future_pct"] = round((float(lows.iloc[idx + 1 : idx + 21].min()) / entry - 1.0) * 100, 2)
                    if highs is not None and pd.isna(row.get("high20_future_pct")) and idx + 20 < len(highs):
                        hist.at[row_idx, "high20_future_pct"] = round((float(highs.iloc[idx + 1 : idx + 21].max()) / entry - 1.0) * 100, 2)
                    trim_price = pd.to_numeric(row.get("trim_price"), errors="coerce")
                    stop_price = pd.to_numeric(row.get("stop_price"), errors="coerce")
                    if lows is not None and highs is not None and not pd.isna(trim_price) and not pd.isna(stop_price):
                        for horizon in [1, 5, 20]:
                            if idx + horizon >= len(closes) or not pd.isna(row.get(f"trim{horizon}_touch_day")):
                                continue
                            for col, value in _sequence_payload(
                                closes=closes,
                                lows=lows,
                                highs=highs,
                                idx=idx,
                                horizon=horizon,
                                trim_price=float(trim_price),
                                stop_price=float(stop_price),
                            ).items():
                                hist.at[row_idx, col] = value

    hist.to_csv(alert_track_csv, index=False, encoding="utf-8-sig")
