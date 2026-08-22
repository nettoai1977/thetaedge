"""
Black-Scholes Options Pricing Model
ThetaEdge - Options Trading Toolkit
"""

import numpy as np
from scipy.stats import norm


def black_scholes(S: float, K: float, T: float, r: float, sigma: float, 
                  option_type: str = 'call', q: float = 0.0) -> float:
    """
    Calculate Black-Scholes option price
    
    Parameters:
    -----------
    S : float
        Current stock price
    K : float
        Strike price
    T : float
        Time to expiration (years)
    r : float
        Risk-free interest rate (annualized)
    sigma : float
        Implied volatility (annualized)
    option_type : str
        'call' or 'put'
    q : float
        Continuous dividend yield (default: 0)
    
    Returns:
    --------
    float
        Option price
    """
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type.lower() == 'call':
        price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    elif option_type.lower() == 'put':
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    else:
        raise ValueError("option_type must be 'call' or 'put'")
    
    return round(price, 4)


def calculate_greeks(S: float, K: float, T: float, r: float, sigma: float,
                     option_type: str = 'call', q: float = 0.0) -> dict:
    """
    Calculate all Greeks for an option
    
    Parameters:
    -----------
    S : float
        Current stock price
    K : float
        Strike price
    T : float
        Time to expiration (years)
    r : float
        Risk-free interest rate (annualized)
    sigma : float
        Implied volatility (annualized)
    option_type : str
        'call' or 'put'
    q : float
        Continuous dividend yield (default: 0)
    
    Returns:
    --------
    dict
        Dictionary with delta, gamma, theta, vega, rho
    """
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    # Delta
    if option_type.lower() == 'call':
        delta = np.exp(-q * T) * norm.cdf(d1)
    else:
        delta = -np.exp(-q * T) * norm.cdf(-d1)
    
    # Gamma (same for calls and puts)
    gamma = np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    # Theta (per day)
    theta = (-(S * sigma * np.exp(-q * T) * norm.pdf(d1)) / (2 * np.sqrt(T))
             - r * K * np.exp(-r * T) * norm.cdf(d2 if option_type == 'call' else -d2)
             + q * S * np.exp(-q * T) * norm.cdf(d1 if option_type == 'call' else -d1)) / 365
    
    if option_type.lower() == 'put':
        theta = (-(S * sigma * np.exp(-q * T) * norm.pdf(d1)) / (2 * np.sqrt(T))
                 + r * K * np.exp(-r * T) * norm.cdf(-d2)
                 - q * S * np.exp(-q * T) * norm.cdf(-d1)) / 365
    
    # Vega (per 1% move)
    vega = S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T) / 100
    
    # Rho (per 1% move)
    if option_type.lower() == 'call':
        rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
    else:
        rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
    
    return {
        'delta': round(delta, 4),
        'gamma': round(gamma, 4),
        'theta': round(theta, 4),
        'vega': round(vega, 4),
        'rho': round(rho, 4)
    }


def implied_volatility(market_price: float, S: float, K: float, T: float, 
                       r: float, option_type: str = 'call', q: float = 0.0,
                       tolerance: float = 1e-6, max_iterations: int = 100) -> float:
    """
    Calculate implied volatility using Newton-Raphson method
    
    Parameters:
    -----------
    market_price : float
        Current market price of the option
    S : float
        Current stock price
    K : float
        Strike price
    T : float
        Time to expiration (years)
    r : float
        Risk-free interest rate (annualized)
    option_type : str
        'call' or 'put'
    q : float
        Continuous dividend yield (default: 0)
    tolerance : float
        Convergence tolerance
    max_iterations : int
        Maximum iterations
    
    Returns:
    --------
    float
        Implied volatility (annualized)
    """
    # Initial guess
    sigma = 0.3
    
    for i in range(max_iterations):
        price = black_scholes(S, K, T, r, sigma, option_type, q)
        diff = price - market_price
        
        if abs(diff) < tolerance:
            return round(sigma, 4)
        
        # Vega (for Newton-Raphson)
        greeks = calculate_greeks(S, K, T, r, sigma, option_type, q)
        vega = greeks['vega'] * 100  # Convert from per 1% to per 1
        
        if abs(vega) < 1e-10:
            break
        
        sigma = sigma - diff / vega
    
    return round(sigma, 4)


def calculate_payoff(positions: list, underlying_prices: np.ndarray) -> np.ndarray:
    """
    Calculate payoff for a multi-leg options position
    
    Parameters:
    -----------
    positions : list
        List of position dictionaries with keys:
        - type: 'call' or 'put'
        - strike: float
        - premium: float
        - quantity: int (positive = long, negative = short)
    underlying_prices : np.ndarray
        Array of underlying prices to calculate P&L for
    
    Returns:
    --------
    np.ndarray
        Array of P&L values for each price point
    """
    payoffs = np.zeros_like(underlying_prices, dtype=float)
    
    for pos in positions:
        if pos['type'].lower() == 'call':
            option_payoff = np.maximum(underlying_prices - pos['strike'], 0)
        else:  # put
            option_payoff = np.maximum(pos['strike'] - underlying_prices, 0)
        
        # For long positions: payoff - premium
        # For short positions: premium - payoff
        if pos['quantity'] > 0:  # Long
            payoffs += pos['quantity'] * (option_payoff - pos['premium'])
        else:  # Short
            payoffs += abs(pos['quantity']) * (pos['premium'] - option_payoff)
    
    return payoffs
