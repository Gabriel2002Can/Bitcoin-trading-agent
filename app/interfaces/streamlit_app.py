from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys
from typing import Any

import pandas as pd
import streamlit as st

try:
    import altair as alt
except Exception:  # pragma: no cover - optional visual dependency
    alt = None

try:
    from app.core.trade_analytics import (
        action_summary_frame,
        daily_trade_counts,
        filter_trade_frame,
        hourly_activity_frame,
        load_trade_frame,
        market_condition_summary,
        market_regime_label,
        summarize_trade_frame,
    )
except ModuleNotFoundError:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from app.core.trade_analytics import (
        action_summary_frame,
        daily_trade_counts,
        filter_trade_frame,
        hourly_activity_frame,
        load_trade_frame,
        market_condition_summary,
        market_regime_label,
        summarize_trade_frame,
    )


st.set_page_config(page_title="Trading Ledger Dashboard", page_icon="📈", layout="wide")


def _inject_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                --bg: #f5f2ec;
                --panel: rgba(255, 255, 255, 0.82);
                --panel-border: rgba(44, 54, 57, 0.10);
                --ink: #1f2a2e;
                --muted: #6a7477;
                --accent: #1f7a6b;
                --accent-2: #c67c3a;
                --accent-3: #8ea7b5;
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(31, 122, 107, 0.10), transparent 30%),
                    radial-gradient(circle at top right, rgba(198, 124, 58, 0.08), transparent 28%),
                    linear-gradient(180deg, #f7f4ef 0%, #f5f2ec 45%, #eef1ef 100%);
                color: var(--ink);
            }

            .hero {
                padding: 1.3rem 1.4rem 1.1rem;
                border-radius: 24px;
                background: linear-gradient(135deg, rgba(255,255,255,0.88), rgba(245, 248, 246, 0.82));
                border: 1px solid var(--panel-border);
                box-shadow: 0 20px 55px rgba(17, 24, 39, 0.08);
                animation: rise 450ms ease-out both;
            }

            .hero h1 {
                margin: 0;
                font-size: 2.15rem;
                letter-spacing: -0.04em;
            }

            .hero p {
                margin: 0.35rem 0 0;
                color: var(--muted);
                font-size: 0.98rem;
                line-height: 1.5;
            }

            .card {
                padding: 1rem 1rem 0.9rem;
                border-radius: 20px;
                background: var(--panel);
                border: 1px solid var(--panel-border);
                box-shadow: 0 12px 30px rgba(17, 24, 39, 0.06);
                min-height: 100%;
                transition: transform 180ms ease, box-shadow 180ms ease;
                animation: rise 400ms ease-out both;
            }

            .card:hover {
                transform: translateY(-2px);
                box-shadow: 0 18px 36px rgba(17, 24, 39, 0.10);
            }

            .card-label {
                color: var(--muted);
                text-transform: uppercase;
                letter-spacing: 0.12em;
                font-size: 0.72rem;
                margin-bottom: 0.35rem;
            }

            .card-value {
                font-size: 1.55rem;
                font-weight: 700;
                color: var(--ink);
                line-height: 1.1;
            }

            .card-caption {
                margin-top: 0.38rem;
                color: var(--muted);
                font-size: 0.84rem;
                line-height: 1.35;
            }

            .section-title {
                margin: 0.8rem 0 0.3rem;
                font-size: 1.08rem;
                letter-spacing: -0.02em;
            }

            @keyframes rise {
                from { opacity: 0; transform: translateY(8px); }
                to { opacity: 1; transform: translateY(0); }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _format_money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "n/a"


def _format_percent(value: Any) -> str:
    try:
        return f"{float(value):+.2%}"
    except Exception:
        return "n/a"


def _format_number(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except Exception:
        return "n/a"


def _render_card(label: str, value: str, caption: str, accent: str = "var(--accent)") -> None:
    st.markdown(
        f"""
        <div class="card">
            <div class="card-label">{label}</div>
            <div class="card-value" style="color: {accent};">{value}</div>
            <div class="card-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=60)
def _load_data() -> pd.DataFrame:
    return load_trade_frame()


def _default_date_range(frame: pd.DataFrame) -> tuple[date, date]:
    if frame.empty:
        today = datetime.now(timezone.utc).date()  # type: ignore[name-defined]
        return today, today

    min_date = frame["trade_date"].min()
    max_date = frame["trade_date"].max()
    return min_date, max_date


def _safe_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return datetime.now(timezone.utc).date()  # type: ignore[name-defined]


_inject_css()

st.markdown(
    """
    <div class="hero">
        <h1>Trading Ledger Dashboard</h1>
        <p>
            A log-first view of the bot's behavior. It tracks today's activity, the weekly picture,
            trade patterns, and market conditions directly from the JSONL archive in <strong>logs/</strong>.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

frame = _load_data()

with st.sidebar:
    st.subheader("Filters")
    st.caption("The ledger reads directly from the stored trade logs.")

    if st.button("Refresh now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if frame.empty:
        st.info("No trade history was found in logs/ yet.")
    else:
        min_date, max_date = _default_date_range(frame)
        selected_range = st.date_input(
            "Date range",
            value=(max(min_date, max_date - timedelta(days=13)), max_date),
            min_value=min_date,
            max_value=max_date,
        )

        if isinstance(selected_range, tuple):
            range_start, range_end = selected_range
        else:
            range_start = range_end = selected_range

        action_options = sorted(frame["action"].dropna().str.lower().unique().tolist())
        strategy_options = sorted(frame["strategy"].fillna("Unknown").astype(str).unique().tolist())

        selected_actions = st.multiselect(
            "Actions",
            options=action_options,
            default=action_options,
        )
        selected_strategies = st.multiselect(
            "Strategies",
            options=strategy_options,
            default=strategy_options,
        )

        show_only_executed = st.checkbox("Only executed trades", value=False)

        selected_frame = filter_trade_frame(
            frame,
            start_date=range_start,
            end_date=range_end,
            actions=selected_actions,
            strategies=selected_strategies,
        )

        if show_only_executed:
            selected_frame = selected_frame[selected_frame["executed"]]

if frame.empty:
    st.warning("No trades have been recorded yet. Once the bot writes to logs/, the dashboard will populate automatically.")
else:
    today = datetime.now(timezone.utc).date()  # type: ignore[name-defined]
    week_start = today - timedelta(days=6)

    today_frame = frame[frame["trade_date"] == today]
    week_frame = frame[frame["trade_date"] >= week_start]
    all_summary = summarize_trade_frame(frame)
    today_summary = summarize_trade_frame(today_frame)
    week_summary = summarize_trade_frame(week_frame)

    top_cards = st.columns(4)
    with top_cards[0]:
        _render_card(
            "Today",
            str(today_summary["total_trades"]),
            f"{today_summary['buy_trades']} buy, {today_summary['sell_trades']} sell, {today_summary['hold_trades']} hold",
            accent="var(--accent)",
        )
    with top_cards[1]:
        _render_card(
            "Last 7 Days",
            str(week_summary["total_trades"]),
            f"Executed ratio {week_summary['executed_ratio']:.0%}",
            accent="var(--accent-2)",
        )
    with top_cards[2]:
        _render_card(
            "All Trades",
            str(all_summary["total_trades"]),
            f"Dominant regime: {market_regime_label(frame)}",
            accent="var(--accent-3)",
        )
    with top_cards[3]:
        latest_trade = frame.iloc[-1]
        latest_label = latest_trade["timestamp"].strftime("%Y-%m-%d %H:%M UTC") if pd.notna(latest_trade["timestamp"]) else "n/a"
        _render_card(
            "Latest Trade",
            str(str(latest_trade.get("action", "n/a")).upper()),
            f"{latest_label} · {latest_trade.get('reason', 'unknown')}",
            accent="var(--ink)",
        )

    st.markdown("<div class=\"section-title\">Today's pulse</div>", unsafe_allow_html=True)
    pulse_cards = st.columns(4)
    with pulse_cards[0]:
        _render_card("Today executed", str(today_summary["executed_trades"]), f"Average value {_format_money(today_summary['avg_trade_value'])}", accent="var(--accent)")
    with pulse_cards[1]:
        _render_card("Today market", market_regime_label(today_frame), market_condition_summary(today_frame), accent="var(--accent-2)")
    with pulse_cards[2]:
        _render_card("Today confidence", _format_percent(today_summary["avg_confidence"]), "Mean model confidence across today's trades.", accent="var(--accent-3)")
    with pulse_cards[3]:
        _render_card("Today RSI", _format_number(today_summary["avg_rsi"]), "Average RSI from the logged trade contexts.", accent="var(--ink)")

    tabs = st.tabs(["Overview", "Patterns", "Ledger", "Raw"])

    with tabs[0]:
        overview_frame = selected_frame.copy()
        if overview_frame.empty:
            st.info("The active filters returned no trades.")
        else:
            overview_summary = summarize_trade_frame(overview_frame)
            chart_area, chart_mix = st.columns([1.7, 1])

            with chart_area:
                st.markdown('<div class="section-title">Price and trade flow</div>', unsafe_allow_html=True)
                if alt is not None:
                    price_chart = (
                        alt.Chart(overview_frame)
                        .mark_line(point=True, strokeWidth=2.2)
                        .encode(
                            x=alt.X("timestamp:T", title="Time"),
                            y=alt.Y("current_price:Q", title="BTC price"),
                            color=alt.Color("action:N", scale=alt.Scale(domain=["buy", "sell", "hold"], range=["#1f7a6b", "#c67c3a", "#75818b"])),
                            tooltip=["timestamp:T", "action:N", "strategy:N", "reason:N", alt.Tooltip("current_price:Q", format=",.2f"), alt.Tooltip("price_change_pct:Q", format=".2%"), alt.Tooltip("opinion_confidence:Q", format=".2%")],
                        )
                        .properties(height=320)
                    )
                    st.altair_chart(price_chart, use_container_width=True)
                else:
                    st.line_chart(overview_frame.set_index("timestamp")["current_price"], height=320)

            with chart_mix:
                st.markdown('<div class="section-title">Action split</div>', unsafe_allow_html=True)
                action_chart_frame = action_summary_frame(overview_frame)
                if alt is not None and not action_chart_frame.empty:
                    action_chart = (
                        alt.Chart(action_chart_frame)
                        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
                        .encode(
                            x=alt.X("action:N", title=None, sort=["buy", "sell", "hold"]),
                            y=alt.Y("count:Q", title="Trades"),
                            color=alt.Color("action:N", scale=alt.Scale(domain=["buy", "sell", "hold"], range=["#1f7a6b", "#c67c3a", "#75818b"])),
                            tooltip=["action:N", "count:Q"],
                        )
                        .properties(height=320)
                    )
                    st.altair_chart(action_chart, use_container_width=True)
                else:
                    st.bar_chart(action_chart_frame.set_index("action")["count"], height=320)

            trend_columns = st.columns(2)
            with trend_columns[0]:
                st.markdown('<div class="section-title">Daily trade count</div>', unsafe_allow_html=True)
                daily_frame = daily_trade_counts(overview_frame)
                if alt is not None and not daily_frame.empty:
                    daily_chart = (
                        alt.Chart(daily_frame)
                        .mark_area(line={"color": "#1f7a6b"}, color="rgba(31, 122, 107, 0.20)")
                        .encode(
                            x=alt.X("trade_date:T", title="Date"),
                            y=alt.Y("count:Q", title="Trades"),
                            tooltip=["trade_date:T", "count:Q"],
                        )
                        .properties(height=240)
                    )
                    st.altair_chart(daily_chart, use_container_width=True)
                else:
                    st.line_chart(daily_frame.set_index("trade_date")["count"], height=240)

            with trend_columns[1]:
                st.markdown('<div class="section-title">Market condition snapshot</div>', unsafe_allow_html=True)
                st.markdown(
                    f"""
                    <div class="card">
                        <div class="card-label">Regime</div>
                        <div class="card-value" style="color: var(--accent-2);">{market_regime_label(overview_frame)}</div>
                        <div class="card-caption">{market_condition_summary(overview_frame)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with tabs[1]:
        pattern_frame = selected_frame.copy()
        if pattern_frame.empty:
            st.info("No trades match the selected filters.")
        else:
            heatmap_columns = st.columns([1.1, 0.9])
            with heatmap_columns[0]:
                st.markdown('<div class="section-title">Trading hours heatmap</div>', unsafe_allow_html=True)
                activity = hourly_activity_frame(pattern_frame)
                if alt is not None and not activity.empty:
                    heatmap = (
                        alt.Chart(activity)
                        .mark_rect(cornerRadius=3)
                        .encode(
                            x=alt.X("trade_hour:O", title="Hour UTC"),
                            y=alt.Y("trade_day_name:O", title="Day of week", sort=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]),
                            color=alt.Color("count:Q", scale=alt.Scale(scheme="tealblues")),
                            tooltip=["trade_day_name:N", "trade_hour:O", "count:Q"],
                        )
                        .properties(height=300)
                    )
                    st.altair_chart(heatmap, use_container_width=True)
                else:
                    st.dataframe(activity, use_container_width=True, hide_index=True)

            with heatmap_columns[1]:
                st.markdown('<div class="section-title">Indicator averages</div>', unsafe_allow_html=True)
                indicator_rows = pd.DataFrame(
                    [
                        {"indicator": "RSI", "value": summarize_trade_frame(pattern_frame)["avg_rsi"]},
                        {"indicator": "ATR", "value": summarize_trade_frame(pattern_frame)["avg_atr"]},
                        {"indicator": "Price change %", "value": summarize_trade_frame(pattern_frame)["avg_price_change_pct"]},
                        {"indicator": "Confidence", "value": summarize_trade_frame(pattern_frame)["avg_confidence"]},
                        {"indicator": "Metrics score", "value": summarize_trade_frame(pattern_frame)["avg_metrics_score"]},
                    ]
                )
                st.dataframe(indicator_rows, use_container_width=True, hide_index=True)

    with tabs[2]:
        ledger_frame = selected_frame.copy().sort_values("timestamp", ascending=False)
        if ledger_frame.empty:
            st.info("No rows match the current filters.")
        else:
            display_columns = [
                "timestamp",
                "action",
                "strategy",
                "reason",
                "value",
                "current_price",
                "price_change_pct",
                "opinion_bias",
                "opinion_confidence",
                "rsi",
                "macd_histogram",
                "atr",
                "portfolio_total_usd",
            ]
            present_columns = [column for column in display_columns if column in ledger_frame.columns]
            st.dataframe(
                ledger_frame[present_columns],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "timestamp": st.column_config.DatetimeColumn("Timestamp", format="YYYY-MM-DD HH:mm"),
                    "value": st.column_config.NumberColumn("Value", format="$%.2f"),
                    "current_price": st.column_config.NumberColumn("BTC price", format="$%.2f"),
                    "price_change_pct": st.column_config.NumberColumn("Price change", format="%.2f%%"),
                    "opinion_confidence": st.column_config.NumberColumn("Confidence", format="%.2f%%"),
                    "rsi": st.column_config.NumberColumn("RSI", format="%.2f"),
                    "macd_histogram": st.column_config.NumberColumn("MACD hist.", format="%.4f"),
                    "atr": st.column_config.NumberColumn("ATR", format="%.2f"),
                    "portfolio_total_usd": st.column_config.NumberColumn("Portfolio USD", format="$%.2f"),
                },
            )

    with tabs[3]:
        st.markdown('<div class="section-title">Raw payloads</div>', unsafe_allow_html=True)
        st.caption("Useful for debugging or verifying the exact serialized trade structure.")
        preview_count = min(len(selected_frame), 10)
        st.json(selected_frame.head(preview_count).to_dict(orient="records"))

