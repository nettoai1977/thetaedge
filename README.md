# ThetaEdge 🎯

**Professional Options Trading Toolkit — Powered by Systematic Strategies**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Status: Complete](https://img.shields.io/badge/Status-Complete-brightgreen.svg)](#)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Deployed-brightgreen)](https://theta-edge-app.web.app)

---

## 📋 Overview

ThetaEdge is a comprehensive options trading toolkit designed for systematic options selling strategies, inspired by Ravish's proven approach that generated $500,000+ in verified profits.

### 🎯 All 4 Phases Complete!

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Strategy Calculator | ✅ Complete |
| 2 | Backtesting Engine | ✅ Complete |
| 3 | Trade Tracker | ✅ Complete |
| 4 | VIX Monitor | ✅ Complete |

**Live App:** https://theta-edge-app.web.app

---

## 🚀 Quick Start

### Option 1: Use Live App (Recommended)

1. Go to https://theta-edge-app.web.app
2. Login with credentials
3. Start using the calculator!

### Option 2: Run Locally

```bash
# Clone the repository
git clone https://github.com/nettoai1977/thetaedge.git
cd thetaedge

# Install Python dependencies
pip install -r requirements.txt

# Start the backend
python -m src.api.main

# Open public/index.html in browser
```

---

## 🧮 Features

### Phase 1: Strategy Calculator
- Black-Scholes pricing engine
- Greeks calculator (Delta, Gamma, Theta, Vega, Rho)
- Interactive payoff diagrams (Chart.js)
- Strategy templates (Double Calendar, Calendar Spread)
- Real-time calculations

### Phase 2: Backtesting Engine
- Double Calendar strategy backtester
- Performance metrics (win rate, profit factor, Sharpe ratio)
- Equity curve visualization
- Configurable parameters

### Phase 3: Trade Tracker
- Add/close/delete trades
- Portfolio summary (win rate, total P&L)
- Open positions view
- Trade history with P&L tracking
- localStorage persistence

### Phase 4: VIX Monitor
- Real-time VIX display
- Entry signal system (ENTER/HOLD/CAUTION/WAIT)
- VIX zones guide
- VIX statistics (7d avg, 30d avg, min, max)
- VIX history chart

---

## 🏗️ Architecture

```
thetaedge/
├── public/                      # Frontend
│   ├── index.html               # Main UI (5 tabs)
│   └── app.js                   # Frontend logic
├── src/
│   ├── engine/                  # Calculation engines
│   │   ├── black_scholes.py     # Black-Scholes pricing
│   │   ├── strategies.py        # Strategy templates
│   │   ├── backtest.py          # Backtesting engine
│   │   ├── tracker.py           # Trade tracker
│   │   └── vix_monitor.py       # VIX monitoring
│   └── api/
│       └── main.py              # FastAPI backend
├── docs/                        # Documentation
│   ├── strategies/              # Strategy guides
│   ├── greeks/                  # Greeks reference
│   ├── moomoo/                  # Broker setup
│   └── backtesting/             # Backtesting guides
├── research/                    # Research documents
│   ├── blueprint.md             # Project blueprint
│   ├── ui-research.md           # UI/UX research
│   └── tech-research.md         # Technical research
├── requirements.txt             # Python dependencies
├── firebase.json                # Firebase config
└── README.md                    # This file
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

## 🎯 Strategies Supported

| Strategy | Win Rate | Risk/Reward | Best Market |
|----------|----------|-------------|-------------|
| Double Calendar | ~80% | 1:1 to 2:1 | Range-bound |
| Time Spread | ~70% | 1:3+ | Slow grind |
| Double Diagonal | ~75% | 1:2 | High IV |

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

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML5 + Tailwind CSS + Chart.js |
| Backend | Python FastAPI |
| Calculation | NumPy + SciPy |
| Hosting | Firebase Hosting |
| Database | localStorage (client-side) |

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

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

## 📧 Contact

**Michael Netto** — Christchurch, New Zealand

- GitHub: [@nettoai1977](https://github.com/nettoai1977)
- Live App: https://theta-edge-app.web.app

---

*Built with ❤️ for systematic options traders*
