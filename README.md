# ThetaEdge 🎯

**Professional Options Trading Toolkit — Powered by Systematic Strategies**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Status: In Development](https://img.shields.io/badge/Status-In%20Development-orange.svg)](#)

---

## 📋 Overview

ThetaEdge is a comprehensive options trading toolkit designed for systematic options selling strategies, inspired by Ravish's proven approach that generated $500,000+ in verified profits.

### Key Features

- 🧮 **Strategy Calculator** — Interactive payoff diagrams with real-time Greeks
- 📊 **Backtesting Engine** — Test strategies on historical data
- 📈 **Trade Tracker** — Log and analyze performance
- ⚡ **VIX Monitor** — Entry signal alerts

---

## 🎯 What is ThetaEdge?

ThetaEdge is built on the principle that **time decay (theta) is your edge**. Instead of predicting market direction, we collect premium systematically:

| Strategy | Win Rate | Risk/Reward | Best Market |
|----------|----------|-------------|-------------|
| Double Calendar | ~80% | 1:1 to 2:1 | Range-bound |
| Time Spread | ~70% | 1:3+ | Slow grind |
| Double Diagonal | ~75% | 1:2 | High IV |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- Moomoo NZ account (for live trading)

### Installation

```bash
# Clone the repository
git clone https://github.com/nettoai1977/thetaedge.git
cd thetaedge

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd src/frontend
npm install
```

### Usage

```bash
# Start the backend
python -m src.api.server

# Start the frontend
cd src/frontend
npm run dev
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Strategy Guide](docs/strategies/README.md) | Complete strategy documentation |
| [Greeks Reference](docs/greeks/README.md) | Options Greeks explained |
| [Moomoo Setup](docs/moomoo/README.md) | NZ broker setup guide |
| [Backtesting Guide](docs/backtesting/README.md) | How to backtest strategies |
| [Project Blueprint](research/blueprint.md) | Technical architecture |

---

## 🏗️ Architecture

```
thetaedge/
├── docs/                    # Documentation
│   ├── strategies/          # Strategy guides
│   ├── greeks/              # Greeks reference
│   ├── moomoo/              # Broker setup
│   └── backtesting/         # Backtesting guides
├── research/                # Research documents
│   ├── blueprint.md         # Project blueprint
│   ├── ui-research.md       # UI/UX research
│   └── tech-research.md     # Technical research
├── src/
│   ├── engine/              # Calculation engine
│   │   ├── black_scholes.py # Black-Scholes model
│   │   ├── greeks.py        # Greeks calculator
│   │   ├── payoff.py        # Payoff diagrams
│   │   └── strategies/      # Strategy templates
│   ├── components/          # Frontend components
│   ├── api/                 # Backend API
│   └── data/                # Data layer
├── scripts/                 # Utility scripts
├── tests/                   # Test suite
└── requirements.txt         # Python dependencies
```

---

## 🧠 Core Concepts

### The Theta Edge

Options lose value over time (theta decay). By selling options, we collect this decay as profit:

```
Short-term option decays faster than long-term option
= Net positive theta
= Profit from time passing
```

### Greeks That Matter

| Greek | What It Means | Our Target |
|-------|---------------|------------|
| **Delta** | Price sensitivity | 20-30 (20-30% ITM chance) |
| **Theta** | Time decay | Positive (we earn theta) |
| **Vega** | Volatility sensitivity | Low IV entry |
| **Gamma** | Delta acceleration | Manage near expiry |

---

## 📊 Performance

Ravish's verified results (Kinfo):
- **Total Profit:** $500,000+
- **Win Rate:** ~80% (actual strategy)
- **Avg Gain/Trade:** 36%
- **Monthly Income:** $50,000-60,000

---

## ⚠️ Risk Disclaimer

> **Options trading involves substantial risk and is not suitable for every investor.**
> 
> - Past performance is not indicative of future results
> - You can lose more than your initial investment
> - Start with paper trading (3-6 months minimum)
> - Never risk money you can't afford to lose
> 
> This is for educational purposes only. Not financial advice.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + TypeScript + Tailwind CSS |
| Charts | Recharts / D3.js |
| Backend | Python FastAPI |
| Calculation | NumPy + SciPy |
| Data | yfinance |
| Database | SQLite |

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

## 📧 Contact

**Michael Netto** — Christchurch, New Zealand

- GitHub: [@nettoai1977](https://github.com/nettoai1977)

---

*Built with ❤️ for systematic options traders*
