from __future__ import annotations

import glob
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd


def _resolve_logs_folder(logs_folder: str | Path | None = None) -> Path:
    if logs_folder is None:
        return Path(__file__).resolve().parents[2] / "logs"

    return Path(logs_folder)


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None

    try:
        normalized_value = str(value).replace("Z", "+00:00")
        parsed_value = datetime.fromisoformat(normalized_value)

        if parsed_value.tzinfo is None:
            return parsed_value.replace(tzinfo=timezone.utc)

        return parsed_value.astimezone(timezone.utc)
    except Exception:
        return None


def _safe_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default

    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def _flatten_trade(trade: dict[str, Any], source_file: str | None = None) -> dict[str, Any]:
    context = trade.get("context") or {}
    opinion = trade.get("opinion") or {}
    portfolio_snapshot = trade.get("portfolio_snapshot") or trade.get("portfolio") or {}

    timestamp = _parse_iso_datetime(trade.get("timestamp"))
    file_timestamp = _parse_iso_datetime(Path(source_file).stem) if source_file else None

    record = {
        "timestamp": timestamp or file_timestamp,
        "source_file": source_file,
        "strategy": trade.get("strategy") or context.get("strategy"),
        "action": str(trade.get("action", "hold")).lower(),
        "reason": trade.get("reason"),
        "value": _safe_float(trade.get("value"), 0.0) or 0.0,
        "metrics_score": _safe_float(trade.get("metrics_score")),
        "scores": trade.get("scores"),
        "dca_triggered": bool(trade.get("dca_triggered", False)),
        "dca_trigger_pct": _safe_float(trade.get("dca_trigger_pct")),
        "opinion_bias": opinion.get("bias"),
        "opinion_confidence": _safe_float(opinion.get("confidence")),
        "opinion_risk_adjustment": _safe_float(opinion.get("risk_adjustment")),
        "opinion_rationale": opinion.get("rationale"),
        "current_price": _safe_float(context.get("current_price")),
        "previous_close": _safe_float(context.get("previous_close")),
        "price_change_pct": _safe_float(context.get("price_change_pct")),
        "stop_loss": _safe_float(context.get("stop_loss")),
        "rsi": _safe_float(context.get("rsi")),
        "ema": _safe_float(context.get("ema")),
        "sma": _safe_float(context.get("sma")),
        "macd": _safe_float(context.get("macd")),
        "macd_signal": _safe_float(context.get("macd_signal")),
        "macd_histogram": _safe_float(context.get("macd_histogram")),
        "atr": _safe_float(context.get("atr")),
        "buy_amount": _safe_float(context.get("buy_amount")),
        "sell_amount": _safe_float(context.get("sell_amount").replace("%","")),
        "sell_amount_is_percent": bool(context.get("sell_amount_is_percent", False)),
        "dca_amount": _safe_float(context.get("dca_amount")),
        "portfolio_cash": _safe_float(portfolio_snapshot.get("cash_balance")),
        "portfolio_btc": _safe_float(portfolio_snapshot.get("btc_holdings")),
        "portfolio_total_usd": _safe_float(portfolio_snapshot.get("total_portfolio_value")),
    }

    if record["timestamp"] is None:
        record["timestamp"] = file_timestamp

    return record


def load_trade_records(logs_folder: str | Path | None = None) -> list[dict[str, Any]]:
    logs_path = _resolve_logs_folder(logs_folder)

    if not logs_path.exists():
        return []

    records: list[dict[str, Any]] = []

    for file_name in sorted(glob.glob(str(logs_path / "*.jsonl"))):
        source_file = Path(file_name).name

        try:
            with open(file_name, "r", encoding="utf-8") as file:
                for line in file:
                    raw_line = line.strip()
                    if not raw_line:
                        continue

                    try:
                        trade = json.loads(raw_line)
                    except Exception:
                        continue

                    if isinstance(trade, dict):
                        records.append(_flatten_trade(trade, source_file=source_file))
        except Exception:
            continue

    records = [record for record in records if record.get("timestamp") is not None]
    records.sort(key=lambda item: item["timestamp"])
    return records


def load_trade_frame(logs_folder: str | Path | None = None) -> pd.DataFrame:
    records = load_trade_records(logs_folder=logs_folder)
    if not records:
        return pd.DataFrame()

    frame = pd.DataFrame(records)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    frame["trade_date"] = frame["timestamp"].dt.date
    frame["trade_week"] = frame["timestamp"].dt.to_period("W-MON").astype(str)
    frame["trade_hour"] = frame["timestamp"].dt.hour
    frame["trade_day_name"] = frame["timestamp"].dt.day_name()
    frame["is_buy"] = frame["action"].eq("buy")
    frame["is_sell"] = frame["action"].eq("sell")
    frame["is_hold"] = frame["action"].eq("hold")
    frame["executed"] = frame["action"].isin(["buy", "sell"])
    frame["price_direction"] = frame["price_change_pct"].apply(
        lambda value: "up" if isinstance(value, (int, float)) and value > 0 else ("down" if isinstance(value, (int, float)) and value < 0 else "flat")
    )
    return frame


def _series_mean(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None

    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    if series.empty:
        return None

    return float(series.mean())


def _series_sum(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame.columns:
        return 0.0

    series = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    return float(series.sum())


def summarize_trade_frame(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "total_trades": 0,
            "buy_trades": 0,
            "sell_trades": 0,
            "hold_trades": 0,
            "executed_trades": 0,
            "avg_confidence": None,
            "avg_metrics_score": None,
            "avg_rsi": None,
            "avg_price_change_pct": None,
            "avg_atr": None,
            "avg_trade_value": None,
            "total_trade_value": 0.0,
            "dominant_strategy": None,
            "dominant_bias": None,
            "first_trade": None,
            "last_trade": None,
        }

    action_counts = frame["action"].value_counts().to_dict()
    strategy_counts = frame["strategy"].fillna("Unknown").value_counts().to_dict()
    bias_counts = frame["opinion_bias"].fillna("neutral").value_counts().to_dict()

    total_trades = int(len(frame))
    buy_trades = int(action_counts.get("buy", 0))
    sell_trades = int(action_counts.get("sell", 0))
    hold_trades = int(action_counts.get("hold", 0))
    executed_trades = buy_trades + sell_trades

    dominant_strategy = next(iter(strategy_counts), None)
    dominant_bias = next(iter(bias_counts), None)

    return {
        "total_trades": total_trades,
        "buy_trades": buy_trades,
        "sell_trades": sell_trades,
        "hold_trades": hold_trades,
        "executed_trades": executed_trades,
        "buy_ratio": buy_trades / total_trades if total_trades else 0.0,
        "sell_ratio": sell_trades / total_trades if total_trades else 0.0,
        "hold_ratio": hold_trades / total_trades if total_trades else 0.0,
        "executed_ratio": executed_trades / total_trades if total_trades else 0.0,
        "avg_confidence": _series_mean(frame, "opinion_confidence"),
        "avg_metrics_score": _series_mean(frame, "metrics_score"),
        "avg_rsi": _series_mean(frame, "rsi"),
        "avg_price_change_pct": _series_mean(frame, "price_change_pct"),
        "avg_atr": _series_mean(frame, "atr"),
        "avg_trade_value": _series_mean(frame, "value"),
        "total_trade_value": _series_sum(frame, "value"),
        "dominant_strategy": dominant_strategy,
        "dominant_bias": dominant_bias,
        "first_trade": frame["timestamp"].min(),
        "last_trade": frame["timestamp"].max(),
    }


def market_regime_label(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No trade history"

    avg_price_change = _series_mean(frame, "price_change_pct") or 0.0
    avg_rsi = _series_mean(frame, "rsi") or 50.0
    avg_histogram = _series_mean(frame, "macd_histogram") or 0.0

    bullish_score = 0
    bearish_score = 0

    if avg_price_change > 0:
        bullish_score += 1
    elif avg_price_change < 0:
        bearish_score += 1

    if avg_rsi >= 55:
        bullish_score += 1
    elif avg_rsi <= 45:
        bearish_score += 1

    if avg_histogram > 0:
        bullish_score += 1
    elif avg_histogram < 0:
        bearish_score += 1

    if bullish_score > bearish_score:
        return "Bullish"
    if bearish_score > bullish_score:
        return "Bearish"
    return "Sideways"


def market_condition_summary(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No market data available yet."

    summary = summarize_trade_frame(frame)
    regime = market_regime_label(frame)
    avg_change = summary.get("avg_price_change_pct") or 0.0
    avg_rsi = summary.get("avg_rsi") or 50.0
    avg_atr = summary.get("avg_atr") or 0.0

    return (
        f"{regime} regime with average intraday move of {avg_change:+.2%}, "
        f"RSI around {avg_rsi:.1f}, and average ATR near {avg_atr:,.2f}."
    )


def _format_money(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.2f}"


def _format_percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.2%}"


def build_weekly_report(trades: Sequence[dict[str, Any]] | pd.DataFrame) -> str:
    if isinstance(trades, pd.DataFrame):
        frame = trades.copy()
    else:
        frame = pd.DataFrame(list(trades)) if trades else pd.DataFrame()

    if not frame.empty and "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        frame = frame.dropna(subset=["timestamp"]).sort_values("timestamp")

    summary = summarize_trade_frame(frame)
    first_trade = summary.get("first_trade")
    last_trade = summary.get("last_trade")
    period_start = first_trade.strftime("%Y-%m-%d %H:%M UTC") if isinstance(first_trade, pd.Timestamp) else (first_trade.isoformat() if isinstance(first_trade, datetime) else "n/a")
    period_end = last_trade.strftime("%Y-%m-%d %H:%M UTC") if isinstance(last_trade, pd.Timestamp) else (last_trade.isoformat() if isinstance(last_trade, datetime) else "n/a")

    if frame.empty:
        return "\n".join([
            "Weekly Trading Report",
            "=====================",
            "",
            "No trades were recorded during the last seven days.",
            "The bot stayed idle and did not receive enough activity to assess market performance.",
        ])

    strategy_counts = frame["strategy"].fillna("Unknown").value_counts()
    reason_counts = frame["reason"].fillna("unknown").value_counts()
    top_strategy = strategy_counts.index[0]
    top_reason = reason_counts.index[0]
    top_reason_count = int(reason_counts.iloc[0])

    market_line = market_condition_summary(frame)

    return "\n".join([
        "Weekly Trading Report",
        "=====================",
        "",
        f"Period: {period_start} -> {period_end}",
        f"Total trades: {summary['total_trades']}",
        f"Executed trades: {summary['executed_trades']} ({summary['executed_ratio']:.1%})",
        f"Buy / Sell / Hold: {summary['buy_trades']} / {summary['sell_trades']} / {summary['hold_trades']}",
        f"Most used strategy: {top_strategy}",
        f"Most common trigger: {top_reason} ({top_reason_count})",
        "",
        "Market conditions",
        "------------------",
        market_line,
        f"Average price change: {_format_percent(summary['avg_price_change_pct'])}",
        f"Average RSI: {summary['avg_rsi']:.1f}" if summary.get("avg_rsi") is not None else "Average RSI: n/a",
        f"Average ATR: {_format_money(summary['avg_atr'])}" if summary.get("avg_atr") is not None else "Average ATR: n/a",
        "",
        "Bot performance",
        "----------------",
        f"Average model confidence: {summary['avg_confidence']:.2%}" if summary.get("avg_confidence") is not None else "Average model confidence: n/a",
        f"Average metrics score: {summary['avg_metrics_score']:+.4f}" if summary.get("avg_metrics_score") is not None else "Average metrics score: n/a",
        f"Average trade size: {_format_money(summary['avg_trade_value'])}" if summary.get("avg_trade_value") is not None else "Average trade size: n/a",
        f"Total traded value: {_format_money(summary['total_trade_value'])}",
        f"Dominant bias: {summary['dominant_bias'] or 'neutral'}",
        "",
        "Interpretation",
        "--------------",
        (
            "The bot leaned into executed trades rather than holding back."
            if summary["executed_trades"] >= summary["hold_trades"]
            else "The bot spent more time waiting for cleaner setups than entering the market."
        ),
        (
            "Momentum and sentiment were aligned with the strategy stack."
            if (summary.get("avg_price_change_pct") or 0.0) >= 0 and (summary.get("avg_rsi") or 50.0) >= 50
            else "Market pressure remained mixed or weak, which explains the more cautious behavior."
        ),
    ])


def filter_trade_frame(
    frame: pd.DataFrame,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    actions: Iterable[str] | None = None,
    strategies: Iterable[str] | None = None,
) -> pd.DataFrame:
    if frame.empty:
        return frame

    filtered = frame.copy()

    if start_date is not None:
        filtered = filtered[filtered["trade_date"] >= start_date]
    if end_date is not None:
        filtered = filtered[filtered["trade_date"] <= end_date]

    if actions:
        action_set = {action.lower() for action in actions}
        filtered = filtered[filtered["action"].isin(action_set)]

    if strategies:
        strategy_set = {str(strategy) for strategy in strategies}
        filtered = filtered[filtered["strategy"].fillna("Unknown").isin(strategy_set)]

    return filtered.sort_values("timestamp")


def daily_trade_counts(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["trade_date", "count"])

    return (
        frame.groupby("trade_date", as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("trade_date")
    )


def hourly_activity_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["trade_day_name", "trade_hour", "count"])

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    activity = (
        frame.groupby(["trade_day_name", "trade_hour"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    activity["trade_day_name"] = pd.Categorical(activity["trade_day_name"], categories=day_order, ordered=True)
    return activity.sort_values(["trade_day_name", "trade_hour"])


def action_summary_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["action", "count"])

    return (
        frame.groupby("action", as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("count", ascending=False)
    )
