# ThetaBrain Automation Architecture

## 🎯 Goal
Automate the trading decision process so it runs 24/7 and alerts you when conditions are met.

## 📊 Automation Levels

### Level 1: Scheduled Analysis (Easy)
- Run ThetaBrain every hour during market hours
- Check VIX, IV Rank, calendar events
- Send alerts when conditions are favorable

### Level 2: Real-Time Monitoring (Medium)
- Monitor price changes continuously
- Detect breakout/breakdown patterns
- Alert on significant moves

### Level 3: Full Automation (Advanced)
- Auto-generate trade ideas
- Auto-calculate position sizes
- Auto-log to trade tracker

## 🏗️ Architecture Options

### Option A: Cron Job + Telegram Bot
```
ThetaBrain Script → Cron (every hour) → Telegram Alert
```
**Pros:** Simple, free, reliable
**Cons:** Not real-time, manual execution

### Option B: Python Scheduler + Webhook
```
APScheduler → ThetaBrain → Webhook → Telegram/Email
```
**Pros:** More flexible, can run complex logic
**Cons:** Requires server/process running

### Option C: Cloud Function + API
```
Cloud Function (scheduled) → ThetaBrain → Push Notification
```
**Pros:** Serverless, scales, reliable
**Cons:** More complex setup

### Option D: Hermes Agent (What We Have!)
```
Hermes Cron Job → ThetaBrain → Telegram Message
```
**Pros:** Already integrated, can use all tools
**Cons:** Requires Hermes running

## 🔧 Recommended: Option D (Hermes Cron)

### Why Hermes Cron?
1. **Already running** — Hermes is always on
2. **Telegram integration** — Messages come directly to you
3. **Full tool access** — Can use terminal, APIs, browser
4. **Flexible scheduling** — Run every hour, every day, etc.
5. **No new infrastructure** — Uses what we have

### Implementation Plan

#### Step 1: Create ThetaBrain Scanner Script
```python
# ~/.hermes/scripts/theta_brain_scanner.py
# Checks market conditions every hour
# Sends Telegram alert when conditions are met
```

#### Step 2: Create Cron Job
```
Schedule: Every hour during market hours (9:30 AM - 4:00 PM ET)
Prompt: Run ThetaBrain scanner, analyze VIX, check tickers, send alert
```

#### Step 3: Alert Format
```
🧠 ThetaBrain Alert

Signal: 🟢 BUY
Ticker: QQQ
Strategy: Double Calendar
IV Rank: 52%
VIX: 14.2

Entry Rules:
✓ VIX at 14.2 - Excellent
✓ IV Rank 52% - High
✓ No FOMC for 14 days

Action: Ready to trade
```

## 📱 Alert Channels

### Telegram (Primary)
- Instant delivery
- Rich formatting
- Mobile notifications
- Already integrated with Hermes

### Email (Backup)
- For detailed reports
- Daily summary
- Weekly review

### SMS (Emergency)
- Only for critical alerts
- Via Twilio (paid)

## ⏰ Schedule Options

### Market Hours (Recommended)
```
Every hour: 9:30 AM - 4:00 PM ET (Mon-Fri)
= Every hour: 2:30 AM - 9:00 AM NZST (Tue-Sat)
```

### Pre-Market
```
Every 30 min: 4:00 AM - 9:30 AM ET
= Every 30 min: 9:00 PM - 2:30 AM NZST
```

### After Hours
```
Every hour: 4:00 PM - 8:00 PM ET
= Every hour: 9:00 AM - 1:00 PM NZST
```

## 🎯 What to Monitor

### VIX Level
- Alert when VIX < 15 (excellent for selling)
- Alert when VIX > 25 (avoid new positions)

### Ticker IV Rank
- Alert when IV Rank > 50% (high premium)
- Alert when IV Rank changes significantly

### Calendar Events
- Alert 2 days before FOMC
- Alert 1 day before CPI
- Alert 1 week before earnings

### Price Alerts
- Alert on 2%+ moves
- Alert at support/resistance levels

## 📊 Output Format

### Daily Morning Brief (8:00 AM NZST)
```
🌅 ThetaBrain Morning Brief

Market Status: Open
VIX: 14.2 (↓ from 15.1)
QQQ IV Rank: 52%

Top Opportunities:
1. QQQ - Double Calendar (85% confidence)
2. SPY - Calendar Spread (70% confidence)

Upcoming Events:
⚠️ FOMC in 3 days
📊 CPI Report Friday

Recommendation: Trade QQQ, avoid SPY until after FOMC
```

### Hourly Scan (During Market Hours)
```
⏰ ThetaBrain Hourly Scan

VIX: 14.2 → 14.5 (stable)
QQQ: $482.50 (+0.5%)

Signal: 🟢 BUY
Strategy: Double Calendar
Strikes: Put $435 / Call $530
Contracts: 2
Risk: $964 (2% of $48,000)

Entry Rules:
✓ VIX excellent
✓ IV Rank 52%
✓ No events for 14 days

Ready to execute? Reply YES to log trade.
```

### Alert (On Condition Change)
```
🚨 ThetaBrain ALERT

Condition: VIX dropped below 15
Previous: 15.2
Current: 14.8

Action: Review opportunities
Tickers: QQQ, SPY, IWM

Reply SCAN for detailed analysis
```

## 🔧 Implementation Steps

1. **Create scanner script** — Python script that runs ThetaBrain
2. **Set up Hermes cron** — Schedule during market hours
3. **Configure alerts** — Telegram messages
4. **Test & refine** — Adjust thresholds and timing
5. **Add logging** — Track all signals and outcomes

## 💡 Future Enhancements

- **Machine Learning** — Learn from past decisions
- **Sentiment Analysis** — Add news sentiment
- **Pattern Recognition** — Detect chart patterns
- **Social Sentiment** — Reddit, Twitter signals
- **Correlation Analysis** — Cross-asset signals
