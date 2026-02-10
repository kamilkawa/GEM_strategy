# pip install yfinance pandas numpy matplotlib

from __future__ import annotations
import os
import tempfile
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# ====== TICKERY (Yahoo) ======
ASSETS = {
    "CNDX": {"yahoo": "CNDX.L", "xtb": "CNDX.UK", "bucket": "RISK"},
    "EIMI": {"yahoo": "EIMI.L", "xtb": "EIMI.UK", "bucket": "RISK"},
    "ISAC": {"yahoo": "ISAC.L", "xtb": "ISAC", "bucket": "RISK"},
    "IB01": {"yahoo": "IB01.L", "xtb": "IB01.UK", "bucket": "SAFE"},
    "CBU0": {"yahoo": "CBU0.L", "xtb": "CBU0.UK", "bucket": "SAFE"},
}

RISK_KEYS = [k for k, v in ASSETS.items() if v["bucket"] == "RISK"]
SAFE_KEY = [k for k, v in ASSETS.items() if v["bucket"] == "SAFE"][0]

START = "2010-01-01"
LOOKBACK_MONTHS = 12
USE_12_1_MOMENTUM = True

COST_BPS = 0


# ====== FIX: yfinance sqlite cache lock ======
def configure_yfinance_cache():
    """
    yfinance potrafi używać sqlite cache (m.in. tz cache). Jeśli równolegle leci kilka zapytań
    albo inny proces trzyma locka, dostaniesz 'database is locked'.
    Ustawiamy osobny katalog cache per uruchomienie.
    """
    cache_dir = os.path.join(tempfile.gettempdir(), f"yfinance_cache_{os.getpid()}")
    os.makedirs(cache_dir, exist_ok=True)

    # W nowszych wersjach yfinance działa:
    # - yf.set_tz_cache_location(path)
    # Jeśli masz starszą, ten call może nie istnieć -> wtedy po prostu polecimy bez niego.
    if hasattr(yf, "set_tz_cache_location"):
        yf.set_tz_cache_location(cache_dir)

    # Dodatkowo: wymuś brak wątków w download() poniżej.
    return cache_dir


def download_monthly_prices(yahoo_tickers: list[str], start: str) -> pd.DataFrame:
    data = yf.download(
        tickers=yahoo_tickers,
        start=start,
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=False,  # <<< kluczowe: bez wątków = mniej locków sqlite
    )

    # Normalizacja formatu
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

    # ME = month end (zamiast deprecated 'M')
    monthly = close.resample("ME").last().dropna(how="all")
    return monthly


def momentum(
    prices_m: pd.DataFrame, lookback: int, use_12_1: bool = True
) -> pd.DataFrame:
    if use_12_1:
        p_num = prices_m.shift(1)
    else:
        p_num = prices_m
    p_den = prices_m.shift(lookback)
    return (p_num / p_den) - 1.0


def build_signals(prices_m: pd.DataFrame) -> pd.DataFrame:
    mom = momentum(prices_m, LOOKBACK_MONTHS, USE_12_1_MOMENTUM)

    risk_cols = [ASSETS[k]["yahoo"] for k in RISK_KEYS]
    safe_col = ASSETS[SAFE_KEY]["yahoo"]

    # zabezpieczenie: zostaw tylko kolumny, które faktycznie istnieją
    risk_cols = [c for c in risk_cols if c in mom.columns]
    if safe_col not in mom.columns:
        raise RuntimeError(f"Brak danych dla SAFE ETF: {safe_col}")

    # usuń wiersze, gdzie wszystkie risk są NA (unikamy idxmax warning/ValueError)
    mom_risk = mom[risk_cols].dropna(how="all")

    best_risk = mom_risk.idxmax(axis=1, skipna=True)
    best_risk_mom = mom_risk.max(axis=1, skipna=True)

    out = pd.DataFrame(index=mom.index)
    out["best_risk_yahoo"] = best_risk
    out["best_risk_mom"] = best_risk_mom

    # absolutny filtr: jeśli best_risk_mom <= 0 -> safe
    out["choice_yahoo"] = np.where(
        out["best_risk_mom"] > 0, out["best_risk_yahoo"], safe_col
    )

    # do podglądu
    for c in mom.columns:
        out[f"mom_{c}"] = mom[c]

    # usuń okres bez lookback
    needed = [f"mom_{safe_col}"] + [f"mom_{c}" for c in risk_cols]
    out = out.dropna(subset=needed)
    return out


def backtest(
    prices_m: pd.DataFrame, signals: pd.DataFrame, cost_bps: float = 0
) -> pd.DataFrame:
    # pct_change: bez deprecated fill_method
    rets = prices_m.pct_change(fill_method=None).dropna(how="all")

    # sygnał z końca miesiąca t obowiązuje w miesiącu t+1
    choice_next = signals["choice_yahoo"].shift(1).reindex(rets.index)

    port_ret = []
    prev = None
    turnover = []

    for dt in rets.index:
        chosen = choice_next.loc[dt]
        if pd.isna(chosen) or chosen not in rets.columns:
            port_ret.append(np.nan)
            turnover.append(0)
            continue

        r = rets.loc[dt, chosen]
        if pd.isna(r):
            port_ret.append(np.nan)
            turnover.append(0)
            continue

        changed = (prev is not None) and (chosen != prev)
        tc = (cost_bps / 10000.0) if (changed and cost_bps > 0) else 0.0
        r_net = (1 + r) * (1 - tc) - 1

        port_ret.append(r_net)
        turnover.append(1 if changed else 0)
        prev = chosen

    bt = pd.DataFrame(index=rets.index)
    bt["choice_yahoo"] = choice_next
    bt["port_ret"] = port_ret
    bt["turnover_flag"] = turnover

    bt = bt.dropna(subset=["port_ret"])
    bt["equity"] = (1 + bt["port_ret"]).cumprod()
    peak = bt["equity"].cummax()
    bt["drawdown"] = bt["equity"] / peak - 1
    return bt


def perf_stats(bt: pd.DataFrame) -> pd.Series:
    n = bt.shape[0]
    years = n / 12.0
    cagr = bt["equity"].iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan

    vol_m = bt["port_ret"].std()
    vol_a = vol_m * np.sqrt(12)

    mean_m = bt["port_ret"].mean()
    mean_a = (1 + mean_m) ** 12 - 1

    sharpe = (mean_a / vol_a) if vol_a > 0 else np.nan
    mdd = bt["drawdown"].min()

    turnover_rate = bt["turnover_flag"].mean() if n > 0 else np.nan

    return pd.Series(
        {
            "CAGR": cagr,
            "Annualized return (approx)": mean_a,
            "Annualized vol": vol_a,
            "Sharpe (rf~0)": sharpe,
            "Max drawdown": mdd,
            "Turnover months %": turnover_rate,
            "Months": n,
        }
    )


def plot_results(bt: pd.DataFrame, title: str):
    plt.figure()
    plt.plot(bt.index, bt["equity"])
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Equity (start=1.0)")
    plt.grid(True)
    plt.show()

    plt.figure()
    plt.plot(bt.index, bt["drawdown"])
    plt.title("Drawdown")
    plt.xlabel("Date")
    plt.ylabel("Drawdown")
    plt.grid(True)
    plt.show()


def main():
    cache_dir = configure_yfinance_cache()
    print(f"[info] yfinance cache dir: {cache_dir}")

    yahoo_tickers = [v["yahoo"] for v in ASSETS.values()]
    prices_m = download_monthly_prices(yahoo_tickers, START)

    # sanity check: co się pobrało?
    print("[info] downloaded columns:", list(prices_m.columns))
    missing = [t for t in yahoo_tickers if t not in prices_m.columns]
    if missing:
        raise RuntimeError(
            f"Brakuje danych dla tickerów: {missing} (sprawdź symbol na Yahoo Finance)"
        )

    signals = build_signals(prices_m)
    bt = backtest(prices_m, signals, cost_bps=COST_BPS)
    stats = perf_stats(bt)

    print("\n=== PERFORMANCE ===")
    # ładny print: %
    printable = stats.copy()
    for k in [
        "CAGR",
        "Annualized return (approx)",
        "Annualized vol",
        "Sharpe (rf~0)",
        "Max drawdown",
        "Turnover months %",
    ]:
        printable[k] = (printable[k] * 100) if pd.notna(printable[k]) else printable[k]
    print(printable)

    # Ostatnie decyzje (XTB)
    yahoo_to_xtb = {v["yahoo"]: v["xtb"] for v in ASSETS.values()}
    tail = bt[["choice_yahoo", "port_ret"]].tail(24).copy()
    tail["choice_xtb"] = tail["choice_yahoo"].map(yahoo_to_xtb)
    tail["port_ret_%"] = (tail["port_ret"] * 100).round(2)
    print("\n=== LAST 24 MONTHS (choices) ===")
    print(tail[["choice_xtb", "port_ret_%"]].to_string())

    title = (
        f"GEM Backtest | 12{'-1' if USE_12_1_MOMENTUM else '-0'} | cost={COST_BPS}bps"
    )
    plot_results(bt, title)


if __name__ == "__main__":
    main()
