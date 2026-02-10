#!/usr/bin/env python3
"""Generate JSON data for the GEM dashboard."""

from __future__ import annotations
import json
import os
import tempfile
from datetime import datetime
import numpy as np
import pandas as pd
import yfinance as yf

# ====== CONFIGURATION: Your ETFs ======
ASSETS = {
    "CNDX": {"yahoo": "CNDX.L", "xtb": "CNDX.UK", "role": "RISK", "name": "NASDAQ 100"},
    "ISAC": {"yahoo": "ISAC.L", "xtb": "ISAC", "role": "RISK", "name": "MSCI ACWI"},
    "EIMI": {"yahoo": "EIMI.L", "xtb": "EIMI.UK", "role": "RISK", "name": "MSCI EM"},
    "IB01": {
        "yahoo": "IB01.L",
        "xtb": "IB01.UK",
        "role": "SAFE",
        "name": "US Treasury 0-1yr",
    },
    "CBU0": {
        "yahoo": "CBU0.L",
        "xtb": "CBU0.UK",
        "role": "SAFE",
        "name": "US Treasury 20+yr",
    },
}

LOOKBACK_MONTHS = 12
USE_12_1_MOMENTUM = True
START = "2008-01-01"
OUTPUT_DIR = "docs"  # GitHub Pages serves from /docs folder


def configure_yfinance_cache() -> str:
    """Avoid yfinance sqlite cache lock by using per-run cache dir."""
    cache_dir = os.path.join(tempfile.gettempdir(), f"yfinance_cache_{os.getpid()}")
    os.makedirs(cache_dir, exist_ok=True)
    if hasattr(yf, "set_tz_cache_location"):
        yf.set_tz_cache_location(cache_dir)
    return cache_dir


def download_monthly_prices(yahoo_tickers: list[str], start: str) -> pd.DataFrame:
    data = yf.download(
        tickers=yahoo_tickers,
        start=start,
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=False,
    )

    if len(yahoo_tickers) == 1:
        close = data["Close"].to_frame(yahoo_tickers[0])
    else:
        close = pd.DataFrame(
            {
                t: data[t]["Close"]
                for t in yahoo_tickers
                if t in data.columns.get_level_values(0)
            }
        )

    close = close.dropna(how="all")
    monthly = close.resample("ME").last().dropna(how="all")
    return monthly


def momentum_12_1(prices_m: pd.DataFrame, lookback: int) -> pd.Series:
    """12-1 momentum for the *latest* month available."""
    if prices_m.shape[0] < lookback + 1:
        raise RuntimeError("Not enough data to calculate 12-1 momentum.")

    p_t1 = prices_m.iloc[-2]  # t-1
    p_t12 = prices_m.iloc[-(lookback + 1)]  # t-12
    return (p_t1 / p_t12) - 1.0


def momentum_series(
    prices_m: pd.DataFrame, lookback: int, use_12_1: bool = True
) -> pd.DataFrame:
    """Calculate momentum time series for backtesting."""
    if use_12_1:
        p_num = prices_m.shift(1)
    else:
        p_num = prices_m
    p_den = prices_m.shift(lookback)
    return (p_num / p_den) - 1.0


def build_signals(prices_m: pd.DataFrame) -> pd.DataFrame:
    """Build signal history for the dashboard."""
    mom = momentum_series(prices_m, LOOKBACK_MONTHS, USE_12_1_MOMENTUM)

    risk_cols = [ASSETS[k]["yahoo"] for k in ASSETS if ASSETS[k]["role"] == "RISK"]
    safe_cols = [ASSETS[k]["yahoo"] for k in ASSETS if ASSETS[k]["role"] == "SAFE"]

    risk_cols = [c for c in risk_cols if c in mom.columns]
    safe_cols = [c for c in safe_cols if c in mom.columns]

    if not safe_cols:
        raise RuntimeError(f"Missing data for SAFE ETFs")

    mom_risk = mom[risk_cols].dropna(how="all")
    mom_safe = mom[safe_cols].dropna(how="all")

    best_risk = mom_risk.idxmax(axis=1, skipna=True)
    best_risk_mom = mom_risk.max(axis=1, skipna=True)

    best_safe = mom_safe.idxmax(axis=1, skipna=True)
    best_safe_mom = mom_safe.max(axis=1, skipna=True)

    out = pd.DataFrame(index=mom.index)
    out["best_risk_yahoo"] = best_risk
    out["best_risk_mom"] = best_risk_mom
    out["best_safe_yahoo"] = best_safe
    out["best_safe_mom"] = best_safe_mom
    out["choice_yahoo"] = np.where(
        out["best_risk_mom"] > 0, out["best_risk_yahoo"], out["best_safe_yahoo"]
    )

    for c in mom.columns:
        out[f"mom_{c}"] = mom[c]

    needed = [f"mom_{c}" for c in safe_cols] + [f"mom_{c}" for c in risk_cols]
    out = out.dropna(subset=needed)
    return out


def backtest(prices_m: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
    """Run backtest for equity curve chart."""
    rets = prices_m.pct_change(fill_method=None).dropna(how="all")
    choice_next = signals["choice_yahoo"].shift(1).reindex(rets.index)

    port_ret = []
    prev = None

    for dt in rets.index:
        chosen = choice_next.loc[dt]
        if pd.isna(chosen) or chosen not in rets.columns:
            port_ret.append(np.nan)
            continue

        r = rets.loc[dt, chosen]
        if pd.isna(r):
            port_ret.append(np.nan)
            continue

        port_ret.append(r)
        prev = chosen

    bt = pd.DataFrame(index=rets.index)
    bt["port_ret"] = port_ret
    bt = bt.dropna(subset=["port_ret"])
    bt["equity"] = (1 + bt["port_ret"]).cumprod()

    return bt


def main():
    configure_yfinance_cache()

    yahoo_map = {k: v["yahoo"] for k, v in ASSETS.items()}
    yahoo_to_key = {v["yahoo"]: k for k, v in ASSETS.items()}
    xtb_map = {v["yahoo"]: v["xtb"] for v in ASSETS.values()}
    name_map = {v["yahoo"]: v["name"] for v in ASSETS.values()}

    yahoo_tickers = list(yahoo_map.values())
    prices_m = download_monthly_prices(yahoo_tickers, START)

    missing = [t for t in yahoo_tickers if t not in prices_m.columns]
    if missing:
        raise RuntimeError(f"Missing data for: {missing}. Check Yahoo Finance tickers.")

    # Current signal
    mom = momentum_12_1(prices_m, LOOKBACK_MONTHS)

    risk_keys = [k for k, v in ASSETS.items() if v["role"] == "RISK"]
    safe_keys = [k for k, v in ASSETS.items() if v["role"] == "SAFE"]

    risk_cols = [yahoo_map[k] for k in risk_keys]
    mom_risk = mom[risk_cols].dropna()

    best_risk_ticker = mom_risk.idxmax()
    best_risk_value = mom_risk.max()

    safe_cols = [yahoo_map[k] for k in safe_keys]
    mom_safe = mom[safe_cols].dropna()

    best_safe_ticker = mom_safe.idxmax()
    best_safe_value = mom_safe.max()

    if best_risk_value > 0:
        choice = best_risk_ticker
        mode = "RISK-ON"
    else:
        choice = best_safe_ticker
        mode = "RISK-OFF"

    last_month_end = prices_m.index[-1].date()
    latest_prices = prices_m.iloc[-1]

    # Build momentum data for all assets
    momentum_data = []
    for ticker in yahoo_tickers:
        key = yahoo_to_key[ticker]
        momentum_data.append(
            {
                "symbol": key,
                "xtb_ticker": xtb_map[ticker],
                "name": name_map[ticker],
                "momentum": float(mom[ticker]) if not pd.isna(mom[ticker]) else 0,
                "price": (
                    float(latest_prices[ticker])
                    if not pd.isna(latest_prices[ticker])
                    else 0
                ),
                "role": ASSETS[key]["role"],
            }
        )

    # Sort by momentum (descending)
    momentum_data.sort(key=lambda x: x["momentum"], reverse=True)

    # Historical signals
    signals = build_signals(prices_m)
    history = []

    for date, row in signals.tail(36).iterrows():  # Last 36 months
        chosen_yahoo = row["choice_yahoo"]
        chosen_key = yahoo_to_key.get(chosen_yahoo, "UNKNOWN")

        history.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "choice": chosen_key,
                "xtb_ticker": xtb_map.get(chosen_yahoo, "N/A"),
                "mode": "RISK-ON" if row["best_risk_mom"] > 0 else "RISK-OFF",
            }
        )

    # Backtest for equity curve
    bt = backtest(prices_m, signals)
    equity_curve = []

    for date, row in bt.iterrows():
        equity_curve.append(
            {"date": date.strftime("%Y-%m-%d"), "equity": float(row["equity"])}
        )

    # Performance stats
    n_months = bt.shape[0]
    years = n_months / 12.0
    total_return = bt["equity"].iloc[-1] - 1
    cagr = (bt["equity"].iloc[-1] ** (1 / years) - 1) if years > 0 else 0

    # Prepare output data
    output = {
        "updated": datetime.now().isoformat(),
        "last_data_date": last_month_end.isoformat(),
        "current_signal": {
            "mode": mode,
            "choice": yahoo_to_key.get(choice, "UNKNOWN"),
            "xtb_ticker": xtb_map.get(choice, "N/A"),
            "name": name_map.get(choice, "Unknown"),
            "best_momentum": (
                float(best_risk_value) if mode == "RISK-ON" else float(best_safe_value)
            ),
        },
        "momentum": momentum_data,
        "history": history,
        "equity_curve": equity_curve,
        "performance": {
            "total_return": float(total_return),
            "cagr": float(cagr),
            "months": int(n_months),
        },
        "config": {"lookback_months": LOOKBACK_MONTHS, "use_12_1": USE_12_1_MOMENTUM},
    }

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Write JSON
    output_file = os.path.join(OUTPUT_DIR, "data.json")
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"✓ Dashboard data generated: {output_file}")
    print(f"✓ Last data date: {last_month_end}")
    print(
        f"✓ Current signal: {mode} → {yahoo_to_key.get(choice)} ({xtb_map.get(choice)})"
    )


if __name__ == "__main__":
    main()
