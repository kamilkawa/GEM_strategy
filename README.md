# GEM - Global Equities Momentum Strategy

A Python implementation of the Global Equities Momentum (GEM) investment strategy with backtesting capabilities. This strategy uses momentum indicators to dynamically allocate between risk assets (equity ETFs) and safe assets (bonds) on a monthly basis.

## 📋 Overview

The GEM strategy uses a **12-1 momentum** calculation to:
- **Risk-On Mode**: When best equity momentum is positive, invest in the equity ETF with the highest momentum
- **Risk-Off Mode**: When all equity ETFs have negative momentum, switch to the bond ETF with the highest momentum (IB01 vs CBU0)

### Supported ETFs

The strategy tracks the following ETFs traded on London Stock Exchange (available on XTB):

| Symbol | XTB Ticker | Description | Role |
|--------|-----------|-------------|------|
| CNDX | CNDX.UK | NASDAQ 100 ETF | RISK |
| ISAC | ISAC | MSCI All Country World ETF | RISK |
| EIMI | EIMI.UK | MSCI Emerging Markets ETF | RISK |
| IB01 | IB01.UK | Treasury Bond 0-1yr ETF | SAFE |
| CBU0 | CBU0.UK | Long-term US Treasury Bonds ETF | SAFE |

## 🚀 Features

- **Monthly Signal Generation**: Calculate trading signals for the next month based on 12-1 momentum
- **Comprehensive Backtesting**: Full backtesting engine with performance metrics
- **Transaction Cost Modeling**: Configurable transaction costs (basis points)
- **Performance Analytics**: CAGR, Sharpe ratio, maximum drawdown, turnover rate
- **Visualization**: Equity curve and drawdown charts
- **Cache Management**: Handles yfinance SQLite cache lock issues

## 📦 Installation

This project uses `uv` for dependency management. Make sure you have Python 3.10+ installed.

```bash
# Clone the repository
git clone <repository-url>
cd GEM

# Install dependencies with uv
uv sync

# Or install manually with pip
pip install -r requirements.txt
```

### Dependencies

- `yfinance>=1.0` - Download market data from Yahoo Finance
- `pandas>=2.3.3` - Data manipulation and analysis
- `numpy>=2.2.6` - Numerical computations
- `matplotlib>=3.10.8` - Visualization

## 💻 Usage

### View Live Dashboard (Recommended)

Simply visit your GitHub Pages URL to see the current signal without running any code:

**[https://kamilkawa.github.io/GEM_strategy/](https://kamilkawa.github.io/GEM_strategy/)**

The dashboard shows:
- Current allocation signal (RISK-ON/RISK-OFF)
- Momentum for all assets
- Last 12 months of signal history

### Generate Monthly Trading Signal

Get the current trading signal for the next month:

```bash
python gem_monthly_signal.py
```

**Output Example:**
```
=== GEM MONTHLY SIGNAL ===
Data (ostatni month-end): 2026-01-31 | cache: /tmp/yfinance_cache_12345
Momentum model: 12-1 | Lookback: 12 miesięcy

--- Momentum 12-1 (dla ETF akcyjnych) ---
CNDX   (CNDX.L )  momentum:    15.23%
ISAC   (ISAC.L )  momentum:    12.45%
EIMI   (EIMI.L )  momentum:     8.91%

--- Decyzja ---
Tryb: RISK-ON
Wybrany ETF (Yahoo): CNDX.L
Wybrany ETF (XTB):  CNDX.UK
Uzasadnienie: Najlepsze momentum > 0 (winner 15.23%)

Uwaga: sygnał liczysz na koniec miesiąca, transakcję robisz na początku kolejnego miesiąca.
```

### Run Backtest

Execute a full historical backtest of the strategy:

```bash
python backtesting.py
```

**Key Features:**
- Historical performance from 2010
- Transaction costs (default: 0 bps - no costs)
- Monthly portfolio selection history
- Visual equity curve and drawdown charts

**Performance Metrics:**
- **CAGR** (Compound Annual Growth Rate)
- **Annualized Return**
- **Annualized Volatility**
- **Sharpe Ratio** (assuming rf≈0)
- **Maximum Drawdown**
- **Turnover Rate** (percentage of months with rebalancing)

## ⚙️ Configuration

### Customize Assets (`gem_monthly_signal.py` or `backtesting.py`)

```python
ASSETS = {
    "CNDX": {"yahoo": "CNDX.L", "xtb": "CNDX.UK", "role": "RISK"},
    "ISAC": {"yahoo": "ISAC.L", "xtb": "ISAC", "role": "RISK"},
    "EIMI": {"yahoo": "EIMI.L", "xtb": "EIMI.UK", "role": "RISK"},
    "IB01": {"yahoo": "IB01.L", "xtb": "IB01.UK", "role": "SAFE"},
    "CBU0": {"yahoo": "CBU0.L", "xtb": "CBU0.UK", "role": "SAFE"},
}
```

### Adjust Parameters (`backtesting.py`)

```python
START = "2010-01-01"          # Backtest start date
LOOKBACK_MONTHS = 12          # Momentum lookback period
USE_12_1_MOMENTUM = True      # Use 12-1 vs 12-0 momentum
COST_BPS = 0                  # Transaction costs (basis points)
```

## 📊 Momentum Calculation

### 12-1 Momentum Formula

```
momentum(t) = [Price(t-1) / Price(t-12)] - 1
```

This measures the **price change from 12 months ago to 1 month ago**, excluding the most recent month to avoid short-term mean reversion.

### Decision Logic

```python
if max(momentum_risk_assets) > 0:
    # RISK-ON: Pick the risk asset with highest momentum
    hold = argmax(momentum_risk_assets)
else:
    # RISK-OFF: Pick the safe asset with highest momentum
    hold = argmax(momentum_safe_assets)  # IB01 vs CBU0
```

## 🌐 Live Dashboard

You can view your GEM strategy signals on a live dashboard hosted on GitHub Pages!

### Live Dashboard

View the dashboard at: **[https://kamilkawa.github.io/GEM_strategy/](https://kamilkawa.github.io/GEM_strategy/)**

The dashboard is automatically updated on the 1st of every month via GitHub Actions.

### Automatic Updates

The dashboard automatically updates on the 1st of every month via GitHub Actions. You can also trigger manual updates:
- Go to Actions tab → "Update GEM Dashboard" → Run workflow

### Local Dashboard Preview

Generate and preview the dashboard locally:

```bash
# Activate virtual environment
source .venv/bin/activate

# Generate dashboard data
python generate_dashboard_data.py

# Open docs/index.html in your browser
open docs/index.html  # macOS
# or
xdg-open docs/index.html  # Linux
```

## 🗂️ Project Structure

```
GEM/
├── README.md                      # This file
├── pyproject.toml                # Project dependencies and metadata
├── gem_monthly_signal.py         # Monthly signal generator (production use)
├── backtesting.py                # Historical backtesting engine
├── generate_dashboard_data.py    # Generate JSON data for dashboard
├── main.py                       # Simple entry point
├── docs/                         # GitHub Pages dashboard
│   ├── index.html               # Dashboard HTML
│   └── data.json                # Generated data (auto-updated)
├── .github/
│   └── workflows/
│       └── update-dashboard.yml  # Auto-update workflow
├── .gitignore                    # Git ignore rules
├── .python-version              # Python version specification
└── uv.lock                      # Dependency lock file
```

## 📈 Strategy Details

### Rebalancing Schedule

- **Signal Calculation**: End of month (last trading day)
- **Execution**: Beginning of next month
- **Frequency**: Monthly

### Risk Management

- **Defensive Allocation**: Automatically switches to bonds when all equity momentum is negative
- **Single Asset Selection**: Concentrated position in the best-performing asset
- **Dynamic Rotation**: Adapts to changing market conditions

## ⚠️ Important Notes

1. **Data Source**: Uses Yahoo Finance data via `yfinance` library
2. **Cache Management**: Handles SQLite cache lock issues automatically
3. **Execution Timing**: Calculate signal at month-end, execute trades at month-start
4. **Transaction Costs**: Default 0 bps (no costs), adjust based on your broker if needed
5. **Backtesting**: Past performance does not guarantee future results

## 🛠️ Troubleshooting

### Database Lock Error

The project automatically handles yfinance SQLite cache locks by creating per-process cache directories. If you still encounter issues, the cache is located in `/tmp/yfinance_cache_<pid>`.

### Missing Data

If you see "Brakuje danych dla tickerów" errors, verify:
1. Ticker symbols are correct for Yahoo Finance
2. Internet connection is active
3. Yahoo Finance API is accessible

## 📝 License

This project is provided as-is for educational and personal use.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

---

**Disclaimer**: This is an educational project. Always do your own research and consider consulting with a financial advisor before making investment decisions.
