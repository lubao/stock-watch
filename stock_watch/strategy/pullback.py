from __future__ import annotations

import pandas as pd


QUALITY_HIGH_RISK = "高風險拉回"
QUALITY_HEALTHY = "健康拉回"
QUALITY_WEAK = "弱承接/疑似破位"
QUALITY_CONFIRM = "需確認拉回"

QUALITY_TO_ACTION = {
    QUALITY_HIGH_RISK: "可小試",
    QUALITY_HEALTHY: "可等買點",
    QUALITY_WEAK: "暫不買",
    QUALITY_CONFIRM: "只觀察",
}

QUALITY_TO_GUIDANCE = {
    QUALITY_HIGH_RISK: "強勢回檔試單：小倉、快停損、不攤平",
    QUALITY_HEALTHY: "正常回檔候選：等支撐確認後再試",
    QUALITY_WEAK: "承接偏弱，先等：等量價恢復再看",
    QUALITY_CONFIRM: "訊號不乾淨，觀察：下一根確認再決定",
}

QUALITY_TO_POSITION_SIZE = {
    QUALITY_HIGH_RISK: "0.25 倉",
    QUALITY_HEALTHY: "0.5 倉",
    QUALITY_WEAK: "0 倉",
    QUALITY_CONFIRM: "0 倉",
}


def _numeric(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def classify_short_pullback_quality(row: pd.Series) -> str:
    if str(row.get("watch_type", "short")) != "short":
        return ""

    risk_value = _numeric(row.get("risk_score"))
    spec_value = _numeric(row.get("spec_risk_score"))
    ret5_value = _numeric(row.get("ret5_pct"))
    ret20_value = _numeric(row.get("ret20_pct"))
    volume_value = _numeric(row.get("volume_ratio20"), 1.0)
    signals = {part.strip().upper() for part in str(row.get("signals", "")).split(",") if part.strip()}
    spec_label = str(row.get("spec_risk_label", "") or "")
    market_heat = str(row.get("market_heat", "") or "")

    if spec_label == "疑似炒作風險高" or spec_value >= 6 or risk_value >= 5 or ret5_value >= 15 or ret20_value >= 30:
        return QUALITY_HIGH_RISK
    if volume_value < 0.9 or ret20_value <= 0 or not (signals & {"TREND", "ACCEL", "REBREAK"}):
        return QUALITY_WEAK
    if risk_value <= 3 and ret5_value >= 4 and ret20_value > 0 and market_heat != "hot":
        return QUALITY_HEALTHY
    return QUALITY_CONFIRM


def pullback_action_label(row: pd.Series) -> str:
    return QUALITY_TO_ACTION.get(classify_short_pullback_quality(row), "只觀察")


def pullback_guidance(row: pd.Series) -> str:
    return QUALITY_TO_GUIDANCE.get(classify_short_pullback_quality(row), QUALITY_TO_GUIDANCE[QUALITY_CONFIRM])


def pullback_position_size(row: pd.Series) -> str:
    return QUALITY_TO_POSITION_SIZE.get(classify_short_pullback_quality(row), "0 倉")


def pullback_action_for_quality(quality: object) -> str:
    return QUALITY_TO_ACTION.get(str(quality or ""), "只觀察")


def pullback_guidance_for_quality(quality: object) -> str:
    return QUALITY_TO_GUIDANCE.get(str(quality or ""), QUALITY_TO_GUIDANCE[QUALITY_CONFIRM])


def pullback_position_for_quality(quality: object) -> str:
    return QUALITY_TO_POSITION_SIZE.get(str(quality or ""), "0 倉")


def next_session_confirmation_bucket(realized_ret_pct: object) -> str:
    ret1_value = _numeric(realized_ret_pct)
    if ret1_value >= 1.0:
        return "隔日轉強"
    if ret1_value >= 0.0:
        return "隔日守住"
    if ret1_value > -2.0:
        return "隔日小跌"
    return "隔日失守"
