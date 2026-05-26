def _portfolio_snapshot(quotation: float, portfolio: dict) -> dict:

    portfolio_dollar = float(
        portfolio.get("portfolio_value").replace(",",".")
        or portfolio.get("Portfolio Value $").replace(",",".")
        or 0.0
    )

    portfolio_btc = float(
        portfolio.get("portfolio_btc").replace(",",".")
        or portfolio.get("Portfolio Value BTC").replace(",",".")
        or 0.0
    )

    total_value_usd = portfolio_dollar + (portfolio_btc * quotation)

    return {
        "portfolio_dollar": portfolio_dollar,
        "portfolio_btc": portfolio_btc,
        "total_value_usd": total_value_usd,
    }

def _format_money(value: float) -> str:
    return f"${value:,.2f}"

def _format_btc(value: float) -> str:
    return f"{value:,.4f} BTC"

def generate_weekly_report(trades):

    try:
        from app.core.trade_analytics import build_weekly_report

        return build_weekly_report(trades)
    except Exception:
        total_trades = len(trades)

        buys = len([
            t for t in trades
            if t.get("action") == "buy" or t.get("decision", {}).get("action") == "buy"
        ])

        sells = len([
            t for t in trades
            if t.get("action") == "sell" or t.get("decision", {}).get("action") == "sell"
        ])

        holds = len([
            t for t in trades
            if t.get("action") == "hold" or t.get("decision", {}).get("action") == "hold"
        ])

        return f"""
Weekly Trading Summary

Total trades: {total_trades}
Buy trades: {buys}
Sell trades: {sells}
Hold decisions: {holds}
"""

def build_trade_message(decision: dict, portfolio: dict) -> str:

    action = decision.get("action", "hold").lower()
    reason = decision.get("reason", "unknown").replace("_", " ")

    value = float(decision.get("value", 0.0))

    context = decision.get("context", {}) or {}
    opinion = decision.get("opinion", {}) or {}

    quotation = float(context.get("current_price", 0.0))

    strategy = decision.get(
        "strategy",
        context.get("strategy", "unknown")
    )

    portfolio = _portfolio_snapshot(quotation, portfolio)

    current_price = float(context.get("current_price", 0.0))
    stop_loss = float(context.get("stop_loss", 0.0))

    rsi = context.get("rsi", 0.0)
    ema = context.get("ema", 0.0)
    sma = context.get("sma", 0.0)

    macd = context.get("macd", 0.0)
    macd_signal = context.get("macd_signal", 0.0)
    macd_histogram = context.get("macd_histogram", 0.0)

    atr = context.get("atr", 0.0)

    price_change_pct = float(
        context.get("price_change_pct", 0.0)
    )

    metrics_score = float(
        decision.get("metrics_score", 0.0)
    )

    bias = opinion.get("bias", "neutral")
    confidence = float(opinion.get("confidence", 0.0))
    rationale = opinion.get(
        "rationale",
        "No rationale provided."
    )

    scores = decision.get("scores", "")

    # =========================
    # HEADLINE
    # =========================

    if action == "buy":
        emoji = "🟢"
        title = "BUY EXECUTED"

    elif action == "sell":
        emoji = "🔴"
        title = "SELL EXECUTED"

    else:
        emoji = "🟡"
        title = "HOLD POSITION"

    lines = [
        f"{emoji} *{title}*",
        "==============================",
        "",
        f"*Strategy:* `{strategy}`",
        f"*Trigger:* `{reason}`",
        "",
    ]

    # =========================
    # TRADE INFO
    # =========================

    if action == "buy":

        btc_bought = value / quotation if quotation else 0.0

        lines.extend([
            "*=== Trade Information ===*",
            f"• Invested: {_format_money(value)}",
            f"• BTC Acquired: {_format_btc(btc_bought)}",
            "",
        ])

    elif action == "sell":

        sell_pct = float(context.get("sell_amount", 0.0).replace("%",""))

        portfolio_btc = portfolio["portfolio_btc"]

        btc_sold = (
            portfolio_btc * sell_pct
            if sell_pct <= 1
            else portfolio_btc * value
        )

        usd_sold = btc_sold * quotation

        lines.extend([
            "*=== Trade Information ===*",
            f"• BTC Sold: {_format_btc(btc_sold)}",
            f"• USD Received: {_format_money(usd_sold)}",
            f"• Sell Portion: {sell_pct:.2%}",
            "",
        ])

    # =========================
    # MARKET INFO
    # =========================

    lines.extend([
        "*=== Market Conditions ===*",
        f"• BTC Price: {_format_money(current_price)}",
        f"• Stop Loss: {_format_money(stop_loss)}",
        f"• ATR: {atr:.4f}",
        f"• Price Change: {price_change_pct:.2%}",
        "",
    ])

    # =========================
    # TECHNICAL INDICATORS
    # =========================

    lines.extend([
        "*=== Technical Indicators ===*",
        f"• RSI: {rsi:.2f}",
        f"• EMA: {ema:.2f}",
        f"• SMA: {sma:.2f}",
        f"• MACD: {macd:.4f}",
        f"• MACD Signal: {macd_signal:.4f}",
        f"• MACD Histogram: {macd_histogram:.4f}",
        "",
    ])

    # =========================
    # AI ANALYSIS
    # =========================

    lines.extend([
        "*=== AI Analysis ===*",
        f"• Bias: `{bias.upper()}`",
        f"• Confidence: {confidence:.2%}",
        f"• Metrics Score: {metrics_score:.4f}",
    ])

    if scores:
        lines.append(f"• Composite Scores: {scores}")

    lines.extend([
        "",
        f"*LLM Insight:*",
        f"_{rationale}_",
        "",
    ])

    # =========================
    # PORTFOLIO
    # =========================

    lines.extend([
        "*=== Portfolio Snapshot ===*",
        f"• Cash Balance: {_format_money(portfolio['portfolio_dollar'])}",
        f"• BTC Holdings: {_format_btc(portfolio['portfolio_btc'])}",
        f"• Total Portfolio Value: {_format_money(portfolio['total_value_usd'])}",
        "",
        "==============================",
    ])

    return "\n".join(lines)