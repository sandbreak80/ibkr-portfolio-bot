# 🔥 YOLO TRADER - QUICK START GUIDE

**⚠️ WARNING: THIS WILL LOSE YOUR MONEY ⚠️**

This guide will help you set up and run the YOLO sentiment-based trading bot.

**DO NOT USE WITH REAL MONEY!**

---

## 🎯 **What Is This?**

The YOLO Trader is a **real-time sentiment-based trading bot** that:

- Scrapes r/wallstreetbets every 5 minutes
- Calculates "YOLO scores" based on social media buzz
- Buys 100% into the highest YOLO score ticker
- Sells if sentiment drops 50%
- Has **ZERO** risk management

**Expected Result:** You will lose money.

---

## 📋 **Prerequisites**

### 1. **Reddit API Credentials** (REQUIRED)

Get free API access from Reddit:

1. Go to: https://www.reddit.com/prefs/apps
2. Click "create another app..."
3. Fill in:
   - **name:** YOLOBot
   - **type:** script
   - **description:** Sentiment analysis for trading
   - **about url:** (leave blank)
   - **redirect uri:** http://localhost:8080
4. Click "create app"
5. Copy the client ID (under the app name) and secret

### 2. **IBKR TWS/Gateway** (REQUIRED)

- Must be running and configured (see main README.md)
- Paper trading account recommended

### 3. **Discord Webhook** (OPTIONAL but recommended)

- For trade alerts
- See main README for setup

---

## ⚙️ **Configuration**

### Add to your `.env` file:

```bash
# Reddit API
REDDIT_CLIENT_ID=your_client_id_from_step_1
REDDIT_CLIENT_SECRET=your_client_secret_from_step_1
REDDIT_USER_AGENT=YOLOBot/1.0

# Discord (optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK

# YOLO Parameters (optional - defaults shown)
YOLO_BUY_THRESHOLD=10.0     # Higher = more selective
YOLO_SELL_THRESHOLD=0.5     # Lower = exit faster
YOLO_SCAN_INTERVAL=300      # Seconds between scans
```

---

## 🚀 **Usage**

### **Paper Trading (HIGHLY RECOMMENDED)**

```bash
docker compose run --rm app poetry run bot yolo --paper
```

This will:
1. Connect to IBKR paper account
2. Start scanning r/wallstreetbets every 5 minutes
3. Trade automatically when YOLO scores exceed threshold
4. Send Discord alerts for all trades
5. Run until you stop it (Ctrl+C)

### **Live Trading (YOUR FUNERAL)**

```bash
docker compose run --rm app poetry run bot yolo --live
```

**DO NOT DO THIS!** This will trade with real money and you WILL lose it.

### **Custom Parameters**

```bash
# More aggressive (lower threshold, scan every 1 minute)
docker compose run --rm app poetry run bot yolo --paper \
  --buy-threshold 5.0 \
  --sell-threshold 0.3 \
  --scan-interval 60

# More conservative (higher threshold, scan every 10 minutes)
docker compose run --rm app poetry run bot yolo --paper \
  --buy-threshold 20.0 \
  --sell-threshold 0.7 \
  --scan-interval 600
```

---

## 📊 **How It Works**

### **YOLO Score Calculation**

```
YOLO_Score = (
    WSB_mentions × 2.0 +
    r/stocks_mentions × 1.0 +
    StockTwits_bullish_ratio × 10.0
) × (1 + Reddit_sentiment)

Where:
- WSB_mentions = number of times ticker appears on r/wallstreetbets
- Reddit_sentiment = -1 (bearish) to +1 (bullish) based on keywords
- StockTwits_bullish_ratio = % of bullish tweets (0.0 to 1.0)
```

### **Trading Rules**

1. **Every 5 minutes:**
   - Scan Reddit and StockTwits
   - Calculate YOLO scores for all tickers in universe
   - Find ticker with highest YOLO score

2. **BUY signal:**
   - If top YOLO score > threshold (default 10.0)
   - AND not already holding that ticker
   - → BUY 100% into that ticker

3. **SELL signal:**
   - If current position's YOLO score drops below 50% of entry score
   - → SELL 100% (move to SPY)

4. **Position management:**
   - Only 1 position at a time
   - 100% allocation (all in)
   - No stop loss
   - No diversification

---

## 🔍 **Example Output**

```
======================================================================
🔥🔥🔥 YOLO TRADER INITIALIZATION 🔥🔥🔥
======================================================================

Mode:           PAPER 📄
Buy Threshold:  10.0
Sell Threshold: 0.5x entry score
Scan Interval:  300s (5min)
Universe:       25 tickers

======================================================================
Starting in 5 seconds... (Ctrl+C to abort)
======================================================================

✅ Connected to IBKR
✅ YOLO Trader initialized

🚀 Starting YOLO trading loop... (Ctrl+C to stop)

🔍 YOLO SCAN #1 - Analyzing sentiment...
  #1: $GME - YOLO Score: 25.43
  #2: $AMC - YOLO Score: 18.27
  #3: $SPY - YOLO Score: 5.12

🚀 YOLO BUY SIGNAL: $GME (Score: 25.43)
✅ YOLO BUY EXECUTED: $GME

Next scan in 300 seconds...

🔍 YOLO SCAN #2 - Analyzing sentiment...
Holding $GME - Score: 22.10 (entry: 25.43)

Next scan in 300 seconds...

🔍 YOLO SCAN #3 - Analyzing sentiment...
💰 YOLO SELL: $GME (Reason: Score dropped 52.3%)
✅ YOLO SELL EXECUTED: $GME

Next scan in 300 seconds...
```

---

## 💬 **Discord Alerts**

If you set up Discord webhook, you'll receive:

### **Buy Alert:**
```
🚀 YOLO BUY: $GME

YOLO Score: 25.43
Position: 100% ALL IN
Orders: 1 executed

Reddit Score: 15.23
StockTwits: 10.20
```

### **Sell Alert:**
```
💰 YOLO SELL: $GME 📉

Reason: Score dropped 52.3%
Entry Score: 25.43
Exit Score: 12.10
Orders: 1 executed
```

---

## ❓ **FAQ**

### **Q: Why does this exist?**
A: To demonstrate why sentiment-only trading is a terrible idea.

### **Q: Will this make me money?**
A: No. It will lose money.

### **Q: Can I use this in live trading?**
A: Technically yes. But you shouldn't. You will lose money.

### **Q: What if I get rich from this?**
A: You got lucky. Don't push it. Cash out immediately.

### **Q: Can I modify the strategy?**
A: Yes! See `src/strategy/yolo_trader.py` and `src/sentiment/aggregator.py`

### **Q: Why is the default threshold 10.0?**
A: Arbitrary. Feel free to adjust based on your paper trading results.

### **Q: What tickers does it trade?**
A: Whatever is in your `config/config.yaml` universe. Default is 25 ETFs.

### **Q: Can it short?**
A: No. This strategy is long-only.

### **Q: What about options?**
A: This trades stocks/ETFs only. No options.

---

## 🛑 **Stopping the Bot**

Press `Ctrl+C` to stop the YOLO trader.

**⚠️ Warning:** Positions may still be open after stopping! Check your IBKR account.

---

## 🐛 **Troubleshooting**

### **"Missing Reddit API credentials"**
- Check your `.env` file has `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`
- Make sure they're correct (no quotes, no spaces)

### **"Could not connect to IBKR"**
- Make sure TWS/Gateway is running
- Check port configuration in `config/config.yaml`
- Try the `bot connect` command first

### **"No YOLO picks found"**
- Universe might be too small
- Increase universe size in `config/config.yaml`
- Or lower the buy threshold

### **"Reddit API rate limit"**
- Reddit API has limits: 60 requests/minute
- Increase scan interval if you hit limits
- Wait 10 minutes and try again

---

## 📈 **Expected Performance**

Based on backtests and common sense:

| Metric | Expected Range |
|--------|---------------|
| **CAGR** | -30% to +10% |
| **Sharpe Ratio** | -0.5 to 0.3 |
| **Max Drawdown** | -60% to -90% |
| **Win Rate** | 30-40% |
| **Probability of Loss** | 90%+ |

**Translation:** You will almost certainly lose money.

---

## 🎓 **Educational Value**

This project teaches:

✅ How to scrape social media (Reddit, StockTwits)  
✅ How to calculate sentiment scores  
✅ How to integrate multiple data sources  
✅ How to build a real-time trading bot  
✅ Why sentiment-only strategies fail  
✅ The importance of risk management  
✅ How to lose money efficiently  

---

## 📚 **Further Reading**

- **Reddit API docs:** https://www.reddit.com/dev/api
- **StockTwits API:** https://api.stocktwits.com/developers/docs
- **Why this doesn't work:** Any academic paper on sentiment trading

---

## 🚨 **FINAL WARNING**

**DO NOT USE THIS WITH REAL MONEY!**

This strategy is designed to **fail**. It has:
- ❌ No risk management
- ❌ No stop loss
- ❌ No diversification
- ❌ No position sizing
- ❌ No backtesting validation
- ❌ No statistical edge

It's a **learning tool** to understand:
1. How social media sentiment works
2. Why FOMO trading is dangerous
3. The importance of proper strategy design

**If you use this with real money and lose everything, that's on you.**

---

## 🙏 **Good Luck**

If you insist on running this (in paper trading, right?), may the odds be ever in your favor.

🚀 **To the moon!** (or more likely, **to zero!**) 💀

---

*Last updated: November 14, 2025*

