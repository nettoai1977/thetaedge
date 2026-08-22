"""
ThetaEdge API - FastAPI Backend
Options Trading Toolkit
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import numpy as np

from ..engine.black_scholes import black_scholes, calculate_greeks, implied_volatility
from ..engine.strategies import StrategyTemplates
from ..engine.backtest import BacktestEngine
from ..engine.tracker import TradeTracker

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
    inputs: Dict[str, Any]


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


class BacktestRequest(BaseModel):
    ticker: str = "QQQ"
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"
    initial_capital: float = 100000
    strategy: str = "double_calendar"
    put_strike_pct: float = 0.90
    call_strike_pct: float = 1.10
    short_days: int = 14
    long_days: int = 30
    iv: float = 0.20
    take_profit_pct: float = 0.30
    stop_loss_pct: float = 0.30


class BacktestResponse(BaseModel):
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
    equity_curve: List[float]
    trades_count: int


class AddTradeRequest(BaseModel):
    ticker: str
    strategy: str
    direction: str
    legs: List[Dict]
    net_debit: float
    contracts: int = 1
    notes: str = ""
    tags: List[str] = []


class CloseTradeRequest(BaseModel):
    trade_id: str
    exit_price: float
    exit_reason: str = "manual"
    notes: str = ""


class TradeResponse(BaseModel):
    id: str
    entry_date: str
    exit_date: Optional[str]
    ticker: str
    strategy: str
    direction: str
    status: str
    legs: List[Dict]
    net_debit: float
    contracts: int
    exit_price: Optional[float]
    pnl: Optional[float]
    pnl_pct: Optional[float]
    exit_reason: Optional[str]
    notes: str
    tags: List[str]


class PortfolioSummary(BaseModel):
    total_trades: int
    closed_trades: int
    open_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    best_trade: Optional[Dict]
    worst_trade: Optional[Dict]


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


@app.post("/api/backtest", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """Run backtest on a strategy"""
    try:
        engine = BacktestEngine(
            ticker=request.ticker,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital
        )
        
        if request.strategy == "double_calendar":
            result = engine.run_double_calendar(
                put_strike_pct=request.put_strike_pct,
                call_strike_pct=request.call_strike_pct,
                short_days=request.short_days,
                long_days=request.long_days,
                iv=request.iv,
                take_profit_pct=request.take_profit_pct,
                stop_loss_pct=request.stop_loss_pct
            )
        else:
            raise HTTPException(status_code=400, detail=f"Strategy {request.strategy} not implemented")
        
        return BacktestResponse(
            strategy=result.strategy,
            ticker=result.ticker,
            start_date=result.start_date,
            end_date=result.end_date,
            total_trades=result.total_trades,
            winning_trades=result.winning_trades,
            losing_trades=result.losing_trades,
            win_rate=result.win_rate,
            total_pnl=result.total_pnl,
            avg_pnl=result.avg_pnl,
            avg_win=result.avg_win,
            avg_loss=result.avg_loss,
            max_drawdown=result.max_drawdown,
            profit_factor=result.profit_factor,
            sharpe_ratio=result.sharpe_ratio,
            equity_curve=result.equity_curve,
            trades_count=len(result.trades)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ Trade Tracker Endpoints ============

tracker = TradeTracker()


@app.get("/api/trades", response_model=List[TradeResponse])
async def get_trades(status: Optional[str] = None):
    """Get all trades, optionally filtered by status"""
    if status == "open":
        trades = tracker.get_open_trades()
    elif status == "closed":
        trades = tracker.get_closed_trades()
    else:
        trades = tracker.trades
    return trades


@app.post("/api/trades", response_model=TradeResponse)
async def add_trade(request: AddTradeRequest):
    """Add a new trade"""
    try:
        trade = tracker.add_trade(
            ticker=request.ticker,
            strategy=request.strategy,
            direction=request.direction,
            legs=request.legs,
            net_debit=request.net_debit,
            contracts=request.contracts,
            notes=request.notes,
            tags=request.tags
        )
        return trade
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/trades/close", response_model=TradeResponse)
async def close_trade(request: CloseTradeRequest):
    """Close an open trade"""
    try:
        trade = tracker.close_trade(
            trade_id=request.trade_id,
            exit_price=request.exit_price,
            exit_reason=request.exit_reason,
            notes=request.notes
        )
        return trade
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/trades/{trade_id}")
async def delete_trade(trade_id: str):
    """Delete a trade"""
    success = tracker.delete_trade(trade_id)
    if not success:
        raise HTTPException(status_code=404, detail="Trade not found")
    return {"status": "deleted"}


@app.get("/api/portfolio", response_model=PortfolioSummary)
async def get_portfolio_summary():
    """Get portfolio performance summary"""
    return tracker.get_performance_summary()


@app.get("/api/portfolio/strategies")
async def get_strategy_breakdown():
    """Get performance breakdown by strategy"""
    return tracker.get_strategy_breakdown()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
