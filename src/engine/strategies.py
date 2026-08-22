"""
Strategy Templates for ThetaEdge
Pre-built strategies: Calendar Spread, Double Calendar, Double Diagonal
"""

import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from .black_scholes import black_scholes, calculate_greeks


@dataclass
class OptionLeg:
    """Single option leg"""
    option_type: str  # 'call' or 'put'
    strike: float
    quantity: int  # positive = long, negative = short
    premium: float
    expiration_days: int


@dataclass
class Strategy:
    """Complete options strategy"""
    name: str
    legs: List[OptionLeg]
    description: str
    entry_criteria: Dict
    exit_rules: Dict


class StrategyTemplates:
    """Pre-built strategy templates"""
    
    @staticmethod
    def calendar_spread(
        S: float,
        K: float,
        r: float = 0.05,
        sigma_short: float = 0.20,
        sigma_long: float = 0.22,
        short_days: int = 14,
        long_days: int = 30,
        option_type: str = 'call'
    ) -> Dict:
        """
        Create a calendar spread
        
        Parameters:
        -----------
        S : float
            Current stock price
        K : float
            Strike price (same for both legs)
        r : float
            Risk-free rate
        sigma_short : float
            IV for short leg
        sigma_long : float
            IV for long leg
        short_days : int
            Days to expiration for short leg
        long_days : int
            Days to expiration for long leg
        option_type : str
            'call' or 'put'
        
        Returns:
        --------
        dict
            Strategy details with Greeks, payoff, and metrics
        """
        T_short = short_days / 365
        T_long = long_days / 365
        
        # Price both options
        short_price = black_scholes(S, K, T_short, r, sigma_short, option_type)
        long_price = black_scholes(S, K, T_long, r, sigma_long, option_type)
        
        # Net debit (cost to enter)
        net_debit = long_price - short_price
        
        # Calculate Greeks for each leg
        short_greeks = calculate_greeks(S, K, T_short, r, sigma_short, option_type)
        long_greeks = calculate_greeks(S, K, T_long, r, sigma_long, option_type)
        
        # Net Greeks (long - short)
        net_greeks = {
            'delta': long_greeks['delta'] - short_greeks['delta'],
            'gamma': long_greeks['gamma'] - short_greeks['gamma'],
            'theta': long_greeks['theta'] - short_greeks['theta'],
            'vega': long_greeks['vega'] - short_greeks['vega'],
            'rho': long_greeks['rho'] - short_greeks['rho']
        }
        
        # Generate payoff diagram
        price_range = np.linspace(S * 0.8, S * 1.2, 100)
        payoffs = []
        
        for price in price_range:
            # At short expiration
            short_option = max(price - K, 0) if option_type == 'call' else max(K - price, 0)
            # Long option still has time value (simplified)
            long_option = black_scholes(price, K, T_long - T_short, r, sigma_long, option_type)
            
            # P&L = long value - short liability - net debit
            pnl = long_option - short_option - net_debit
            payoffs.append(pnl)
        
        payoffs = np.array(payoffs)
        
        return {
            'name': f'Calendar {option_type.upper()} Spread',
            'legs': [
                {'type': option_type, 'strike': K, 'quantity': -1, 'premium': short_price, 'days': short_days},
                {'type': option_type, 'strike': K, 'quantity': 1, 'premium': long_price, 'days': long_days}
            ],
            'net_debit': round(net_debit, 2),
            'max_profit': round(max(payoffs), 2),
            'max_loss': round(net_debit, 2),
            'breakeven': round(K, 2),  # Simplified
            'net_greeks': {k: round(v, 4) for k, v in net_greeks.items()},
            'payoff_prices': price_range.tolist(),
            'payoff_values': payoffs.tolist(),
            'description': f'Sell {short_days}D {option_type}, Buy {long_days}D {option_type} at ${K}',
            'entry_criteria': {
                'vix': '< 20',
                'market': 'Range-bound',
                'delta': '20-30'
            }
        }
    
    @staticmethod
    def double_calendar(
        S: float,
        put_strike: float,
        call_strike: float,
        r: float = 0.05,
        sigma: float = 0.20,
        short_days: int = 14,
        long_days: int = 30
    ) -> Dict:
        """
        Create a double calendar spread
        
        Parameters:
        -----------
        S : float
            Current stock price
        put_strike : float
            Put strike price (lower)
        call_strike : float
            Call strike price (upper)
        r : float
            Risk-free rate
        sigma : float
            Implied volatility
        short_days : int
            Days to expiration for short leg
        long_days : int
            Days to expiration for long leg
        
        Returns:
        --------
        dict
            Strategy details with Greeks, payoff, and metrics
        """
        T_short = short_days / 365
        T_long = long_days / 365
        
        # Price all four options
        short_put = black_scholes(S, put_strike, T_short, r, sigma, 'put')
        long_put = black_scholes(S, put_strike, T_long, r, sigma, 'put')
        short_call = black_scholes(S, call_strike, T_short, r, sigma, 'call')
        long_call = black_scholes(S, call_strike, T_long, r, sigma, 'call')
        
        # Net debit
        net_debit = (long_put - short_put) + (long_call - short_call)
        
        # Calculate Greeks
        short_put_greeks = calculate_greeks(S, put_strike, T_short, r, sigma, 'put')
        long_put_greeks = calculate_greeks(S, put_strike, T_long, r, sigma, 'put')
        short_call_greeks = calculate_greeks(S, call_strike, T_short, r, sigma, 'call')
        long_call_greeks = calculate_greeks(S, call_strike, T_long, r, sigma, 'call')
        
        # Net Greeks
        net_greeks = {
            'delta': (long_put_greeks['delta'] - short_put_greeks['delta']) + 
                     (long_call_greeks['delta'] - short_call_greeks['delta']),
            'gamma': (long_put_greeks['gamma'] - short_put_greeks['gamma']) + 
                     (long_call_greeks['gamma'] - short_call_greeks['gamma']),
            'theta': (long_put_greeks['theta'] - short_put_greeks['theta']) + 
                     (long_call_greeks['theta'] - short_call_greeks['theta']),
            'vega': (long_put_greeks['vega'] - short_put_greeks['vega']) + 
                    (long_call_greeks['vega'] - short_call_greeks['vega']),
            'rho': (long_put_greeks['rho'] - short_put_greeks['rho']) + 
                   (long_call_greeks['rho'] - short_call_greeks['rho'])
        }
        
        # Generate payoff diagram
        price_range = np.linspace(S * 0.7, S * 1.3, 200)
        payoffs = []
        
        for price in price_range:
            # Put spread payoff
            short_put_payoff = max(put_strike - price, 0)
            long_put_payoff = black_scholes(price, put_strike, max(T_long - T_short, 0.001), r, sigma, 'put')
            put_spread = long_put_payoff - short_put_payoff
            
            # Call spread payoff
            short_call_payoff = max(price - call_strike, 0)
            long_call_payoff = black_scholes(price, call_strike, max(T_long - T_short, 0.001), r, sigma, 'call')
            call_spread = long_call_payoff - short_call_payoff
            
            # Total P&L
            pnl = put_spread + call_spread - net_debit
            payoffs.append(pnl)
        
        payoffs = np.array(payoffs)
        
        return {
            'name': 'Double Calendar Spread',
            'legs': [
                {'type': 'put', 'strike': put_strike, 'quantity': -1, 'premium': short_put, 'days': short_days},
                {'type': 'put', 'strike': put_strike, 'quantity': 1, 'premium': long_put, 'days': long_days},
                {'type': 'call', 'strike': call_strike, 'quantity': -1, 'premium': short_call, 'days': short_days},
                {'type': 'call', 'strike': call_strike, 'quantity': 1, 'premium': long_call, 'days': long_days}
            ],
            'net_debit': round(net_debit, 2),
            'max_profit': round(max(payoffs), 2),
            'max_loss': round(net_debit, 2),
            'breakeven_low': round(put_strike, 2),
            'breakeven_high': round(call_strike, 2),
            'net_greeks': {k: round(v, 4) for k, v in net_greeks.items()},
            'payoff_prices': price_range.tolist(),
            'payoff_values': payoffs.tolist(),
            'description': f'Double Calendar: Put ${put_strike} / Call ${call_strike}',
            'entry_criteria': {
                'vix': '15-20',
                'market': 'Range-bound',
                'strikes': '~10% OTM each side'
            }
        }
    
    @staticmethod
    def double_diagonal(
        S: float,
        short_put_strike: float,
        short_call_strike: float,
        long_put_strike: float,
        long_call_strike: float,
        r: float = 0.05,
        sigma: float = 0.25,
        short_days: int = 14,
        long_days: int = 30
    ) -> Dict:
        """
        Create a double diagonal spread
        
        Parameters:
        -----------
        S : float
            Current stock price
        short_put_strike : float
            Short put strike (higher)
        short_call_strike : float
            Short call strike (lower)
        long_put_strike : float
            Long put strike (lower than short put)
        long_call_strike : float
            Long call strike (higher than short call)
        r : float
            Risk-free rate
        sigma : float
            Implied volatility
        short_days : int
            Days to expiration for short leg
        long_days : int
            Days to expiration for long leg
        
        Returns:
        --------
        dict
            Strategy details with Greeks, payoff, and metrics
        """
        T_short = short_days / 365
        T_long = long_days / 365
        
        # Price all four options
        short_put = black_scholes(S, short_put_strike, T_short, r, sigma, 'put')
        long_put = black_scholes(S, long_put_strike, T_long, r, sigma, 'put')
        short_call = black_scholes(S, short_call_strike, T_short, r, sigma, 'call')
        long_call = black_scholes(S, long_call_strike, T_long, r, sigma, 'call')
        
        # Net debit
        net_debit = (long_put - short_put) + (long_call - short_call)
        
        # Generate payoff diagram
        price_range = np.linspace(S * 0.7, S * 1.3, 200)
        payoffs = []
        
        for price in price_range:
            # Put spread payoff
            short_put_payoff = max(short_put_strike - price, 0)
            long_put_payoff = black_scholes(price, long_put_strike, max(T_long - T_short, 0.001), r, sigma, 'put')
            put_spread = long_put_payoff - short_put_payoff
            
            # Call spread payoff
            short_call_payoff = max(price - short_call_strike, 0)
            long_call_payoff = black_scholes(price, long_call_strike, max(T_long - T_short, 0.001), r, sigma, 'call')
            call_spread = long_call_payoff - short_call_payoff
            
            # Total P&L
            pnl = put_spread + call_spread - net_debit
            payoffs.append(pnl)
        
        payoffs = np.array(payoffs)
        
        return {
            'name': 'Double Diagonal',
            'legs': [
                {'type': 'put', 'strike': short_put_strike, 'quantity': -1, 'premium': short_put, 'days': short_days},
                {'type': 'put', 'strike': long_put_strike, 'quantity': 1, 'premium': long_put, 'days': long_days},
                {'type': 'call', 'strike': short_call_strike, 'quantity': -1, 'premium': short_call, 'days': short_days},
                {'type': 'call', 'strike': long_call_strike, 'quantity': 1, 'premium': long_call, 'days': long_days}
            ],
            'net_debit': round(net_debit, 2),
            'max_profit': round(max(payoffs), 2),
            'max_loss': round(net_debit, 2),
            'payoff_prices': price_range.tolist(),
            'payoff_values': payoffs.tolist(),
            'description': f'Double Diagonal: Put ${long_put_strike}/${short_put_strike} / Call ${short_call_strike}/${long_call_strike}',
            'entry_criteria': {
                'vix': '> 20',
                'market': 'High IV',
                'expectation': 'IV decrease'
            }
        }
