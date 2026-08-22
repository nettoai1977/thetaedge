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
from ..engine.vix_monitor import VIXMonitor
from ..engine.market_calendar import MarketCalendar
from ..engine.ticker_scanner import TickerScanner
from ..engine.position_sizer import PositionSizer
from ..engine.theta_brain import ThetaBrain, MarketInputs

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


class VIXResponse(BaseModel):
    current: float
    avg_7d: float
    avg_30d: float
    min_30d: float
    max_30d: float
    signal: str
    interpretation: str
    readings_count: int


class EntrySignalResponse(BaseModel):
    signal: str
    confidence: str
    message: str
    strategies: List[str]
    color: str


class VIXReadingResponse(BaseModel):
    timestamp: str
    value: float
    signal: str
    interpretation: str


class MarketStatusResponse(BaseModel):
    status: str
    status_label: str
    us_time: str
    nz_time: Optional[str]
    next_event: Optional[str]
    is_trading_day: bool
    is_holiday: bool


class CalendarEventResponse(BaseModel):
    date: str
    type: str
    name: str
    importance: str
    market_closed: Optional[bool]
    time: Optional[str]
    day_name: Optional[str]
    days_until: Optional[int]


class TickerDataResponse(BaseModel):
    symbol: str
    name: str
    price: float
    change_pct: float
    volume: int
    avg_volume: int
    iv_rank: float
    iv_percentile: float
    beta: float
    sector: str
    earnings_date: Optional[str]
    has_earnings_soon: bool
    liquidity_score: float
    recommendation: str


class TickerDetailsResponse(BaseModel):
    ticker: TickerDataResponse
    strategy_recommendation: Dict
    entry_criteria: Dict


class PositionSizeRequest(BaseModel):
    net_debit: float
    max_loss_pct: float = 100
    risk_pct: float = 2.0
    account_size: float = 10000


class PositionSizeResponse(BaseModel):
    account_size: float
    risk_per_trade_pct: float
    max_loss_per_trade: float
    contracts: int
    total_risk: float
    risk_remaining: float
    recommendation: str


class BrainAnalyzeRequest(BaseModel):
    vix_level: float
    vix_trend: str = "stable"
    symbol: str = "QQQ"
    price: float = 500
    iv_rank: float = 40
    volume: int = 10000000
    avg_volume: int = 15000000
    days_to_fomc: Optional[int] = None
    days_to_cpi: Optional[int] = None
    days_to_earnings: Optional[int] = None
    current_positions: int = 0
    account_size: float = 10000
    current_risk_pct: float = 5.0


class BrainOutputResponse(BaseModel):
    signal: str
    signal_strength: str
    recommended_strategy: str
    strategy_confidence: str
    suggested_put_strike: float
    suggested_call_strike: float
    recommended_contracts: int
    max_risk_dollars: float
    entry_rules: List[str]
    exit_rules: List[str]
    warnings: List[str]
    reasoning: List[str]


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


# ============ VIX Monitor Endpoints ============

vix_monitor = VIXMonitor()


@app.get("/api/vix", response_model=VIXResponse)
async def get_vix():
    """Get current VIX data and statistics"""
    reading = vix_monitor.record_reading()
    return vix_monitor.get_statistics()


@app.get("/api/vix/signal", response_model=EntrySignalResponse)
async def get_entry_signal():
    """Get entry signal for Ravish's strategies"""
    return vix_monitor.get_entry_signal()


@app.get("/api/vix/history", response_model=List[VIXReadingResponse])
async def get_vix_history(days: int = 30):
    """Get VIX readings history"""
    return vix_monitor.get_readings_history(days)


@app.post("/api/vix/record", response_model=VIXReadingResponse)
async def record_vix_reading(value: Optional[float] = None):
    """Record a VIX reading"""
    return vix_monitor.record_reading(value)


# ============ Market Calendar Endpoints ============

calendar = MarketCalendar()


@app.get("/api/market/status", response_model=MarketStatusResponse)
async def get_market_status():
    """Get current market status"""
    return calendar.get_market_status()


@app.get("/api/market/holidays")
async def get_holidays(year: int = 2025):
    """Get market holidays"""
    return calendar.get_holidays(year)


@app.get("/api/market/fomc")
async def get_fomc_dates(year: int = 2025):
    """Get FOMC meeting dates"""
    return calendar.get_fomc_dates(year)


@app.get("/api/market/events", response_model=List[CalendarEventResponse])
async def get_calendar_events(month: int = None, year: int = None):
    """Get calendar events for a month"""
    if month is None:
        month = datetime.now().month
    if year is None:
        year = datetime.now().year
    return calendar.get_calendar_events(month, year)


@app.get("/api/market/upcoming", response_model=List[CalendarEventResponse])
async def get_upcoming_events(days: int = 7):
    """Get upcoming events"""
    return calendar.get_upcoming_events(days)


@app.get("/api/market/hours-nz")
async def get_market_hours_nz():
    """Get market hours in NZ time"""
    return calendar.get_market_hours_nz()


# ============ Ticker Scanner Endpoints ============

scanner = TickerScanner()


@app.get("/api/tickers/scan", response_model=List[TickerDataResponse])
async def scan_tickers():
    """Scan all popular tickers"""
    return scanner.scan_all()


@app.get("/api/tickers/best", response_model=List[TickerDataResponse])
async def get_best_tickers(limit: int = 5):
    """Get best tickers for trading"""
    return scanner.get_best_tickers(limit)


@app.get("/api/tickers/{symbol}", response_model=TickerDetailsResponse)
async def get_ticker_details(symbol: str):
    """Get detailed ticker analysis"""
    return scanner.get_ticker_details(symbol.upper())


# ============ Position Sizing Endpoints ============

sizer = PositionSizer()


@app.post("/api/position/calculate", response_model=PositionSizeResponse)
async def calculate_position_size(request: PositionSizeRequest):
    """Calculate position size"""
    sizer.account_size = request.account_size
    return sizer.calculate(
        net_debit=request.net_debit,
        max_loss_pct=request.max_loss_pct,
        risk_pct=request.risk_pct
    )


# ============ ThetaBrain Endpoints ============

brain = ThetaBrain()


@app.post("/api/brain/analyze", response_model=BrainOutputResponse)
async def analyze_trade(request: BrainAnalyzeRequest):
    """Analyze trade with ThetaBrain"""
    inputs = MarketInputs(
        vix_level=request.vix_level,
        vix_trend=request.vix_trend,
        symbol=request.symbol,
        price=request.price,
        iv_rank=request.iv_rank,
        volume=request.volume,
        avg_volume=request.avg_volume,
        days_to_fomc=request.days_to_fomc,
        days_to_cpi=request.days_to_cpi,
        days_to_earnings=request.days_to_earnings,
        current_positions=request.current_positions,
        account_size=request.account_size,
        current_risk_pct=request.current_risk_pct
    )
    return brain.analyze(inputs)


@app.get("/api/brain/quick")
async def quick_assessment(vix: float = 18, iv_rank: float = 40):
    """Quick brain assessment"""
    return brain.get_quick_assessment(vix, iv_rank)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
