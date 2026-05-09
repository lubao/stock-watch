from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

from stock_watch.reports.common import dataframe_to_html


def _table_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_None_"
    headers = [str(c) for c in df.columns.tolist()]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        values = []
        for col in headers:
            value = row.get(col)
            if pd.isna(value):
                text = ""
            elif isinstance(value, float) and value.is_integer():
                text = str(int(value))
            else:
                text = str(value)
            values.append(text.replace("|", "\\|").replace("\n", " "))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_portfolio_risk_panel(review: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "total_positions",
        "total_value",
        "attack_exposure_pct",
        "core_exposure_pct",
        "defensive_exposure_pct",
        "high_risk_exposure_pct",
        "volatile_exposure_pct",
        "stop_distance_risk_pct",
        "near_escape_positions",
        "profit_take_positions",
    ]
    if review.empty:
        return pd.DataFrame(columns=columns)

    work = review.copy()
    empty_numeric = pd.Series(index=work.index, dtype=float)
    work["position_value"] = pd.to_numeric(work.get("position_value", empty_numeric), errors="coerce").fillna(0.0)
    work["current_close"] = pd.to_numeric(work.get("current_close", empty_numeric), errors="coerce")
    work["escape_price"] = pd.to_numeric(work.get("escape_price", empty_numeric), errors="coerce")
    work["shares"] = pd.to_numeric(work.get("shares", empty_numeric), errors="coerce").fillna(0.0)
    total_value = float(work["position_value"].sum())

    def _exposure_pct(mask: pd.Series) -> float:
        if total_value <= 0:
            return 0.0
        return round(float(work.loc[mask, "position_value"].sum() / total_value * 100.0), 1)

    holding_style = work.get("holding_style", pd.Series(index=work.index, dtype=object)).fillna("").astype(str)
    risk_score = pd.to_numeric(work.get("risk_score", empty_numeric), errors="coerce").fillna(0)
    spec_risk_score = pd.to_numeric(work.get("spec_risk_score", empty_numeric), errors="coerce").fillna(0)
    spec_risk_label = work.get("spec_risk_label", pd.Series(index=work.index, dtype=object)).fillna("").astype(str)
    volatility_tag = work.get("volatility_tag", pd.Series(index=work.index, dtype=object)).fillna("").astype(str)
    advice = work.get("advice", pd.Series(index=work.index, dtype=object)).fillna("").astype(str)

    downside = ((work["current_close"] - work["escape_price"]).clip(lower=0) * work["shares"]).fillna(0.0)
    stop_distance_risk_pct = round(float(downside.sum() / total_value * 100.0), 1) if total_value > 0 else 0.0
    near_escape = (work["current_close"].notna()) & (work["escape_price"].notna()) & (work["current_close"] <= work["escape_price"] * 1.03)
    profit_take = advice.str.contains("落袋|達標", regex=True)
    high_risk = (risk_score >= 5) | (spec_risk_score >= 6) | (spec_risk_label == "疑似炒作風險高")

    return pd.DataFrame(
        [
            {
                "total_positions": int(len(work)),
                "total_value": round(total_value, 0),
                "attack_exposure_pct": _exposure_pct(holding_style == "進攻持股"),
                "core_exposure_pct": _exposure_pct(holding_style == "核心持股"),
                "defensive_exposure_pct": _exposure_pct(holding_style == "防守持股"),
                "high_risk_exposure_pct": _exposure_pct(high_risk),
                "volatile_exposure_pct": _exposure_pct(volatility_tag == "劇烈"),
                "stop_distance_risk_pct": stop_distance_risk_pct,
                "near_escape_positions": int(near_escape.sum()),
                "profit_take_positions": int(profit_take.sum()),
            }
        ],
        columns=columns,
    )


def build_portfolio_report_markdown(
    df_rank: pd.DataFrame,
    market_regime: dict,
    us_market: dict,
    *,
    build_portfolio_review_df: Callable[[pd.DataFrame, dict, dict], pd.DataFrame],
    build_market_scenario: Callable[[dict, dict, pd.DataFrame], dict],
    realtime_quote_interval: str,
    realtime_quotes_enabled: bool,
    auto_added_tickers: Iterable[str],
    volatility_badge_text: Callable[[pd.Series], str],
) -> str:
    review = build_portfolio_review_df(df_rank, market_regime, us_market)
    risk_panel = build_portfolio_risk_panel(review)
    scenario = build_market_scenario(market_regime, us_market, df_rank)
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    quote_line = f"- Quote: realtime({realtime_quote_interval}) if available, else daily close"
    if not realtime_quotes_enabled:
        quote_line = "- Quote: daily close (realtime disabled)"
    lines = [
        "# Portfolio Review",
        f"- Generated: {today}",
        f"- Market Regime: {market_regime['comment']}",
        f"- US Summary: {us_market['summary']}",
        f"- Market Scenario: {scenario['label']} | {scenario['stance']}",
        f"- Exit Focus: {scenario['exit_note']}",
        quote_line,
        "",
    ]
    auto_added_tickers = list(auto_added_tickers)
    if auto_added_tickers:
        lines.append(f"- Auto-added to watchlist: {', '.join(auto_added_tickers)}")
        lines.append("")

    lines.extend(["## Portfolio Risk Panel", "", _table_markdown(risk_panel), ""])
    lines.extend(["## Holdings", ""])
    if review.empty:
        lines.append("- None")
        return "\n".join(lines)

    for _, row in review.iterrows():
        current_close = row.get("current_close")
        if pd.isna(current_close):
            lines.append(f"- {row['ticker'].split('.')[0]} | {row['advice']} | 尚未抓到行情，已同步加入觀察清單")
            continue
        lines.append(
            f"- {row['name']} ({row['ticker'].split('.')[0]}) | {row['holding_style']} | 現價 {round(float(current_close), 2)} | "
            f"成本 {round(float(row['avg_cost']), 2)} | 報酬 {row['unrealized_pnl_pct']}% | "
            f"目標 {row['target_profit_pct']}% | 波動 {volatility_badge_text(row)} | 建議 {row['advice']} | "
            f"價格帶 {row.get('price_plan', '')}"
        )
    return "\n".join(lines)


def build_portfolio_report_html(
    df_rank: pd.DataFrame,
    market_regime: dict,
    us_market: dict,
    *,
    build_portfolio_review_df: Callable[[pd.DataFrame, dict, dict], pd.DataFrame],
    build_market_scenario: Callable[[dict, dict, pd.DataFrame], dict],
    auto_added_tickers: Iterable[str],
) -> str:
    review = build_portfolio_review_df(df_rank, market_regime, us_market)
    risk_panel = build_portfolio_risk_panel(review)
    scenario = build_market_scenario(market_regime, us_market, df_rank)
    review_html = "<p>None</p>" if review.empty else dataframe_to_html(review)
    risk_panel_html = "<p>None</p>" if risk_panel.empty else dataframe_to_html(risk_panel)
    auto_added_tickers = list(auto_added_tickers)
    auto_added_html = ""
    if auto_added_tickers:
        auto_added_html = f"<p><strong>Auto-added to watchlist:</strong> {', '.join(auto_added_tickers)}</p>"
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Portfolio Review</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; }}
th, td {{ border: 1px solid #ddd; padding: 8px; font-size: 14px; }}
th {{ background: #f4f4f4; }}
</style></head><body>
<h1>Portfolio Review</h1>
<p><strong>Market:</strong> {market_regime['comment']}</p>
<p><strong>US Summary:</strong> {us_market['summary']}</p>
<p><strong>Scenario:</strong> {scenario['label']} | {scenario['stance']}</p>
	<p><strong>Exit Focus:</strong> {scenario['exit_note']}</p>
	{auto_added_html}
	<h2>Portfolio Risk Panel</h2>{risk_panel_html}
	<h2>Holdings</h2>{review_html}
	</body></html>"""


def save_portfolio_reports(
    df_rank: pd.DataFrame,
    market_regime: dict,
    us_market: dict,
    *,
    markdown_path: Path,
    html_path: Path,
    build_portfolio_review_df: Callable[[pd.DataFrame, dict, dict], pd.DataFrame],
    build_market_scenario: Callable[[dict, dict, pd.DataFrame], dict],
    realtime_quote_interval: str,
    realtime_quotes_enabled: bool,
    auto_added_tickers: Iterable[str],
    volatility_badge_text: Callable[[pd.Series], str],
) -> None:
    markdown_path.write_text(
        build_portfolio_report_markdown(
            df_rank,
            market_regime,
            us_market,
            build_portfolio_review_df=build_portfolio_review_df,
            build_market_scenario=build_market_scenario,
            realtime_quote_interval=realtime_quote_interval,
            realtime_quotes_enabled=realtime_quotes_enabled,
            auto_added_tickers=auto_added_tickers,
            volatility_badge_text=volatility_badge_text,
        ),
        encoding="utf-8",
    )
    html_path.write_text(
        build_portfolio_report_html(
            df_rank,
            market_regime,
            us_market,
            build_portfolio_review_df=build_portfolio_review_df,
            build_market_scenario=build_market_scenario,
            auto_added_tickers=auto_added_tickers,
        ),
        encoding="utf-8",
    )
