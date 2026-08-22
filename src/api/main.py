"""
ThetaEdge API - FastAPI Backend
Options Trading Toolkit
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import numpy as np

from ..engine.black_scholes import black_scholes, calculate_greeks, implied_volatility
from ..engine.strategies import StrategyTemplates

app = FastAPI(
    title="ThetaEdge API",
    description="Options Trading Toolkit - Powered by Systematic Strategies",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Request/Response Models ============

class OptionPricingRequest(BaseModel):
    stock_price: float
    strike_price: float
    days_to_expiry: int
    risk_free_rate: float = 0.05
    implied_volatility: float = 0.20
    option_type: str = "call"
    dividend_yield: float = 0.0


class OptionPricingResponse(BaseModel):
    price: float
    greeks: Dict[str, float]
    inputs: Dict[str, float]


class CalendarSpreadRequest(BaseModel):
    stock_price: float
    strike_price: float
    risk_free_rate: float = 0.05
    sigma_short: float = 0.20
    sigma_long: float = 0.22
    short_days: int = 14
    long_days: int = 30
    option_type: str = "call"


class DoubleCalendarRequest(BaseModel):
    stock_price: float
    put_strike: float
    call_strike: float
    risk_free_rate: float = 0.05
    implied_volatility: float = 0.20
    short_days: int = 14
    long_days: int = 30


class StrategyResponse(BaseModel):
    name: str
    legs: List[Dict]
    net_debit: float
    max_profit: float
    max_loss: float
    net_greeks: Dict[str, float]
    payoff_prices: List[float]
    payoff_values: List[float]
    description: str
    entry_criteria: Dict


# ============ API Endpoints ============

@app.get("/")
async def root():
    return {
        "name": "ThetaEdge API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "pricing": "/api/pricing",
            "greeks": "/api/greeks",
            "strategies": {
                "calendar": "/api/strategy/calendar",
                "double_calendar": "/api/strategy/double-calendar",
                "double_diagonal": "/api/strategy/double-diagonal"
            }
        }
    }


@app.post("/api/pricing", response_model=OptionPricingResponse)
async def calculate_price(request: OptionPricingRequest):
    """Calculate option price using Black-Scholes"""
    try:
        T = request.days_to_expiry / 365
        price = black_scholes(
            S=request.stock_price,
            K=request.strike_price,
            T=T,
            r=request.risk_free_rate,
            sigma=request.implied_volatility,
            option_type=request.option_type,
            q=request.dividend_yield
        )
        
        greeks = calculate_greeks(
            S=request.stock_price,
            K=request.strike_price,
            T=T,
            r=request.risk_free_rate,
            sigma=request.implied_volatility,
            option_type=request.option_type,
            q=request.dividend_yield
        )
        
        return OptionPricingResponse(
            price=price,
            greeks=greeks,
            inputs={
                "stock_price": request.stock_price,
                "strike_price": request.strike_price,
                "days_to_expiry": request.days_to_expiry,
                "risk_free_rate": request.risk_free_rate,
                "implied_volatility": request.implied_volatility,
                "option_type": request.option_type
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/greeks")
async def get_greeks(request: OptionPricingRequest):
    """Calculate Greeks for an option"""
    try:
        T = request.days_to_expiry / 365
        greeks = calculate_greeks(
            S=request.stock_price,
            K=request.strike_price,
            T=T,
            r=request.risk_free_rate,
            sigma=request.implied_volatility,
            option_type=request.option_type,
            q=request.dividend_yield
        )
        return {"greeks": greeks}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/strategy/calendar", response_model=StrategyResponse)
async def create_calendar_spread(request: CalendarSpreadRequest):
    """Create a calendar spread strategy"""
    try:
        result = StrategyTemplates.calendar_spread(
            S=request.stock_price,
            K=request.strike_price,
            r=request.risk_free_rate,
            sigma_short=request.sigma_short,
            sigma_long=request.sigma_long,
            short_days=request.short_days,
            long_days=request.long_days,
            option_type=request.option_type
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/strategy/double-calendar", response_model=StrategyResponse)
async def create_double_calendar(request: DoubleCalendarRequest):
    """Create a double calendar spread strategy"""
    try:
        result = StrategyTemplates.double_calendar(
            S=request.stock_price,
            put_strike=request.put_strike,
            call_strike=request.call_strike,
            r=request.risk_free_rate,
            sigma=request.implied_volatility,
            short_days=request.short_days,
            long_days=request.long_days
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/strategy/double-diagonal", response_model=StrategyResponse)
async def create_double_diagonal(
    stock_price: float,
    short_put_strike: float,
    short_call_strike: float,
    long_put_strike: float,
    long_call_strike: float,
    risk_free_rate: float = 0.05,
    implied_volatility: float = 0.25,
    short_days: int = 14,
    long_days: int = 30
):
    """Create a double diagonal spread strategy"""
    try:
        result = StrategyTemplates.double_diagonal(
            S=stock_price,
            short_put_strike=short_put_strike,
            short_call_strike=short_call_strike,
            long_put_strike=long_put_strike,
            long_call_strike=long_call_strike,
            r=risk_free_rate,
            sigma=implied_volatility,
            short_days=short_days,
            long_days=long_days
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ThetaEdge API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
