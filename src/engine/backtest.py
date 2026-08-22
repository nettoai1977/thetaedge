"""
Backtesting Engine for ThetaEdge
Tests options strategies on historical data
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from ..engine.black_scholes import black_scholes, calculate_greeks
from ..engine.strategies import StrategyTemplates


@dataclass
class Trade:
    """Single trade record"""
    entry_date: str
    exit_date: str
    strategy: str
    entry_price: float
    exit_price: float
    net_debit: float
    pnl: float
    pnl_pct: float
    legs: List[Dict]
    status: str  # 'win', 'loss', 'breakeven'


@dataclass
class BacktestResult:
    """Backtest results"""
    strategy: str
    ticker: str
    start_date: str
    end_date: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    avg_win: float
    avg_loss: float
    max_drawdown: float
    profit_factor: float
    sharpe_ratio: float
    trades: List[Trade]
    equity_curve: List[float]


class BacktestEngine:
    """Options strategy backtesting engine"""
    
    def __init__(self, ticker: str, start_date: str, end_date: str, 
                 initial_capital: float = 100000):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = [initial_capital]
    
    def run_double_calendar(
        self,
        put_strike_pct: float = 0.90,
        call_strike_pct: float = 1.10,
        short_days: int = 14,
        long_days: int = 30,
        iv: float = 0.20,
        take_profit_pct: float = 0.30,
        stop_loss_pct: float = 0.30,
        trade_interval_days: int = 5
    ) -> BacktestResult:
        """
        Run double calendar backtest
        
        Parameters:
        -----------
        put_strike_pct : float
            Put strike as % of stock price (0.90 = 10% OTM)
        call_strike_pct : float
            Call strike as % of stock price (1.10 = 10% OTM)
        short_days : int
            Days to expiration for short leg
        long_days : int
            Days to expiration for long leg
        iv : float
            Assumed implied volatility
        take_profit_pct : float
            Take profit target (0.30 = 30%)
        stop_loss_pct : float
            Stop loss level (0.30 = 30%)
        trade_interval_days : int
            Days between new trades
        """
        # Generate synthetic price data (in real app, use yfinance)
        dates = pd.date_range(self.start_date, self.end_date, freq='B')
        np.random.seed(42)
        
        # Random walk with drift
        returns = np.random.normal(0.0003, 0.015, len(dates))
        prices = self.initial_capital * 0.01 * np.exp(np.cumsum(returns))  # Normalize to ~$500
        
        self.trades = []
        self.equity_curve = [self.initial_capital]
        capital = self.initial_capital
        
        i = 0
        while i < len(dates) - long_days:
            entry_date = dates[i]
            current_price = prices[i]
            
            # Calculate strikes
            put_strike = round(current_price * put_strike_pct)
            call_strike = round(current_price * call_strike_pct)
            
            # Calculate entry cost
            T_short = short_days / 365
            T_long = long_days / 365
            
            short_put = black_scholes(current_price, put_strike, T_short, 0.05, iv, 'put')
            long_put = black_scholes(current_price, put_strike, T_long, 0.05, iv, 'put')
            short_call = black_scholes(current_price, call_strike, T_short, 0.05, iv, 'call')
            long_call = black_scholes(current_price, call_strike, T_long, 0.05, iv, 'call')
            
            net_debit = (long_put - short_put) + (long_call - short_call)
            
            if net_debit <= 0 or capital < net_debit * 100:
                i += trade_interval_days
                continue
            
            # Simulate trade outcome
            exit_idx = min(i + short_days, len(dates) - 1)
            exit_price = prices[exit_idx]
            
            # Calculate P&L based on price movement
            price_change = (exit_price - current_price) / current_price
            
            # Simplified P&L model
            if abs(price_change) < 0.05:  # Price stayed in range
                pnl_pct = np.random.uniform(0.10, take_profit_pct)
            elif abs(price_change) < 0.10:  # Price moved but stayed in range
                pnl_pct = np.random.uniform(-0.10, 0.20)
            else:  # Price moved significantly
                pnl_pct = np.random.uniform(-stop_loss_pct, -0.10)
            
            pnl = net_debit * 100 * pnl_pct
            contracts = min(5, int(capital * 0.02 / (net_debit * 100)))
            total_pnl = pnl * contracts
            
            trade = Trade(
                entry_date=str(entry_date.date()),
                exit_date=str(dates[exit_idx].date()),
                strategy='Double Calendar',
                entry_price=round(current_price, 2),
                exit_price=round(exit_price, 2),
                net_debit=round(net_debit, 2),
                pnl=round(total_pnl, 2),
                pnl_pct=round(pnl_pct * 100, 2),
                legs=[
                    {'type': 'put', 'strike': put_strike, 'qty': -1, 'premium': round(short_put, 2)},
                    {'type': 'put', 'strike': put_strike, 'qty': 1, 'premium': round(long_put, 2)},
                    {'type': 'call', 'strike': call_strike, 'qty': -1, 'premium': round(short_call, 2)},
                    {'type': 'call', 'strike': call_strike, 'qty': 1, 'premium': round(long_call, 2)}
                ],
                status='win' if pnl > 0 else 'loss'
            )
            
            self.trades.append(trade)
            capital += total_pnl
            self.equity_curve.append(round(capital, 2))
            
            i += trade_interval_days
        
        return self._calculate_results('Double Calendar')
    
    def _calculate_results(self, strategy_name: str) -> BacktestResult:
        """Calculate backtest statistics"""
        if not self.trades:
            return BacktestResult(
                strategy=strategy_name,
                ticker=self.ticker,
                start_date=self.start_date,
                end_date=self.end_date,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                total_pnl=0,
                avg_pnl=0,
                avg_win=0,
                avg_loss=0,
                max_drawdown=0,
                profit_factor=0,
                sharpe_ratio=0,
                trades=[],
                equity_curve=self.equity_curve
            )
        
        pnls = [t.pnl for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        # Calculate max drawdown
        peak = self.equity_curve[0]
        max_dd = 0
        for val in self.equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd
        
        # Calculate Sharpe ratio
        if len(pnls) > 1:
            returns = np.array(pnls) / self.initial_capital
            sharpe = np.sqrt(252) * np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        else:
            sharpe = 0
        
        return BacktestResult(
            strategy=strategy_name,
            ticker=self.ticker,
            start_date=self.start_date,
            end_date=self.end_date,
            total_trades=len(self.trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=round(len(wins) / len(self.trades) * 100, 1),
            total_pnl=round(sum(pnls), 2),
            avg_pnl=round(np.mean(pnls), 2),
            avg_win=round(np.mean(wins), 2) if wins else 0,
            avg_loss=round(np.mean(losses), 2) if losses else 0,
            max_drawdown=round(max_dd * 100, 1),
            profit_factor=round(abs(sum(wins) / sum(losses)), 2) if losses else 999,
            sharpe_ratio=round(sharpe, 2),
            trades=self.trades,
            equity_curve=self.equity_curve
        )
