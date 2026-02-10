#!/usr/bin/env python3
# pip install yfinance pandas numpy

from __future__ import annotations
import os
import tempfile
import numpy as np
import pandas as pd
import yfinance as yf


# ====== KONFIGURACJA: Twoje ETFy ======
ASSETS = {
    # key: {yahoo symbol, xtb symbol, role}
    "CNDX": {"yahoo": "CNDX.L", "xtb": "CNDX.UK", "role": "RISK"},
    "ISAC": {"yahoo": "ISAC.L", "xtb": "ISAC", "role": "RISK"},
    "EIMI": {"yahoo": "EIMI.L", "xtb": "EIMI.UK", "role": "RISK"},
    "IB01": {"yahoo": "IB01.L", "xtb": "IB01.UK", "role": "SAFE"},
    "CBU0": {"yahoo": "CBU0.L", "xtb": "CBU0.UK", "role": "SAFE"},
}

LOOKBACK_MONTHS = 12
USE_12_1_MOMENTUM = True
START = "2008-01-01"  # wystarczy dużo wcześniej niż 12 mies.


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
        # create a flat Close dataframe from the multiindex output
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
    """
    12-1 momentum for the *latest* month available:
      mom(t) = P(t-1)/P(t-12) - 1
    """
    if prices_m.shape[0] < lookback + 1:
        raise RuntimeError("Za mało danych do policzenia 12-1 momentum.")

    p_t1 = prices_m.iloc[-2]  # t-1
    p_t12 = prices_m.iloc[-(lookback + 1)]  # t-12
    return (p_t1 / p_t12) - 1.0


def main():
    cache_dir = configure_yfinance_cache()

    risk_keys = [k for k, v in ASSETS.items() if v["role"] == "RISK"]
    safe_keys = [k for k, v in ASSETS.items() if v["role"] == "SAFE"]
    safe_key = safe_keys[0]  # primary SAFE asset for strategy

    yahoo_map = {k: v["yahoo"] for k, v in ASSETS.items()}
    xtb_map = {v["yahoo"]: v["xtb"] for v in ASSETS.values()}

    yahoo_tickers = [yahoo_map[k] for k in ASSETS.keys()]
    prices_m = download_monthly_prices(yahoo_tickers, START)

    # sanity check
    missing = [t for t in yahoo_tickers if t not in prices_m.columns]
    if missing:
        raise RuntimeError(f"Brakuje danych dla: {missing}. Sprawdź tickery Yahoo.")

    # compute latest momentum
    mom = momentum_12_1(prices_m, LOOKBACK_MONTHS)

    # only risk assets participate in 'winner'
    risk_cols = [yahoo_map[k] for k in risk_keys]
    mom_risk = mom[risk_cols].dropna()

    best_ticker = mom_risk.idxmax()
    best_value = mom_risk.max()

    safe_ticker = yahoo_map[safe_key]

    if best_value > 0:
        choice = best_ticker
        mode = "RISK-ON"
        reason = f"Najlepsze momentum > 0 (winner {best_value:.2%})"
    else:
        choice = safe_ticker
        mode = "RISK-OFF"
        reason = f"Wszystkie momentum ≤ 0 (best {best_value:.2%})"

    # month label: decision for next month after last completed month
    last_month_end = prices_m.index[-1].date()
    signal_month = prices_m.index[-1].strftime(
        "%Y-%m"
    )  # month of last datapoint (month-end)
    # momentum is based on t-1 and t-12, but computed at month-end t; practical: trade at start of next month.

    print("\n=== GEM MONTHLY SIGNAL ===")
    print(f"Data (ostatni month-end): {last_month_end} | cache: {cache_dir}")
    print(
        f"Momentum model: 12{'-1' if USE_12_1_MOMENTUM else '-0'} | Lookback: {LOOKBACK_MONTHS} miesięcy"
    )
    print("\n--- Momentum 12-1 (dla ETF akcyjnych) ---")
    for k in risk_keys:
        y = yahoo_map[k]
        print(f"{k:5s}  ({y:7s})  momentum: {mom[y]*100:8.2f}%")

    print("\n--- Decyzja ---")
    print(f"Tryb: {mode}")
    print(f"Wybrany ETF (Yahoo): {choice}")
    print(f"Wybrany ETF (XTB):  {xtb_map.get(choice, 'N/A')}")
    print(f"Uzasadnienie: {reason}")

    print("\n--- Dodatkowo: momentum SAFE assets ---")
    for k in safe_keys:
        y = yahoo_map[k]
        is_primary = " (używany w strategii)" if k == safe_key else ""
        print(f"{k:5s} ({y:7s}) momentum: {mom[y]*100:8.2f}%{is_primary}")
    print(
        "\nUwaga: sygnał liczysz na koniec miesiąca, transakcję robisz na początku kolejnego miesiąca.\n"
    )


if __name__ == "__main__":
    main()
